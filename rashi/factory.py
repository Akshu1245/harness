"""Software factory (his 2026-11-27 ask): a code-defined closed loop for coding agents.

A factory.json in the workdir IS the loop definition, versioned with the code: goal,
acceptance checks, protected fixtures, iteration/time bounds, git mode, and whether an
agent reviewer gates completion. Each iteration of the closed loop:

  write    - the coding agent edits the tree (any callable or agent CLI)
  checks   - the caller's check commands run; exit codes decide, model claims never do
  commit   - the final tree of the iteration is committed to LOCAL git history
  review   - optional: a reviewer agent reads the committed diff and ACCEPTs or REJECTs
  feedback - failing check output or the review rejection goes back to the coding agent

DONE_VERIFIED only when every check exits 0 and the reviewer (if configured) accepts and
every declared artifact exists. Anything else is an honest FAILED_*/STOPPED_* status.
Commits never leave the machine: the factory runs no push and touches no remote. These
are cooperative checks, not containment against hostile processes.

artifacts: the definition may declare previewable outputs (an HTML app, a doc) the run
must produce, the artifacts-style deliverable. A DONE loop missing one reports
FAILED_ARTIFACT_MISSING instead. `rashi preview DIR` serves the workdir on 127.0.0.1 so
the artifact opens like a real page; nothing is uploaded or shared.
"""
import functools
import hashlib
import http.server
import json
import subprocess
from pathlib import Path

from .contract import validate as _validate_contract
from .loop import emit, run_loop
from .orchestrate import CliAgent

# Loop bookkeeping is runtime state, not product code: keep it out of factory commits.
EXCLUDE = [":(exclude)events.jsonl", ":(exclude)PROGRESS.json", ":(exclude).rashi",
           ":(exclude).spill", ":(exclude).replay.jsonl"]


class FactoryError(Exception):
    pass


def load(path, workdir):
    """Read and validate a factory definition. Checks/protected reuse the caller-contract
    rules (contract.validate), so factory and one-press acceptance enforce the same shape."""
    try:
        defn = json.loads(Path(path).read_text())
    except (OSError, ValueError) as ex:
        raise FactoryError(f"unreadable factory definition: {ex}")
    if not isinstance(defn, dict):
        raise FactoryError("factory definition must be a JSON object")
    goal = defn.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise FactoryError("factory definition requires a nonempty goal")
    try:
        core = _validate_contract({"checks": defn.get("checks"),
                                   "protected": defn.get("protected", [])}, workdir)
    except ValueError as ex:
        raise FactoryError(str(ex))
    review = defn.get("review", False)
    if not isinstance(review, bool):
        raise FactoryError("review must be a boolean")
    artifacts = defn.get("artifacts", [])
    if (not isinstance(artifacts, list) or
            any(not isinstance(a, str) or not a.strip() for a in artifacts)):
        raise FactoryError("artifacts must be a list of relative paths")
    for rel in artifacts:
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts:
            raise FactoryError("unsafe artifact path")
    git = defn.get("git", True)
    if not (isinstance(git, bool) or git == "init"):
        raise FactoryError('git must be true, false or "init"')
    out = {"goal": goal, **core, "review": review, "git": git, "artifacts": artifacts,
           "max_iters": defn.get("max_iters", 6), "max_seconds": defn.get("max_seconds", 900)}
    for key in ("max_iters", "max_seconds"):
        value = out[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise FactoryError(f"{key} must be a positive integer")
    return out


def definition_hash(defn):
    """Stable identity of the validated definition: show it before a run, record it after."""
    return hashlib.sha256(json.dumps(defn, sort_keys=True).encode()).hexdigest()


def _git(workdir, *args):
    """Local git with a loop identity set per command; never touches global config or remotes."""
    return subprocess.run(["git", "-c", "user.name=rashi-factory",
                           "-c", "user.email=rashi-factory@localhost", *args],
                          cwd=workdir, capture_output=True, text=True, timeout=60)


def ensure_repo(workdir, mode):
    """True: a repo must already exist. "init": create one. False: run unversioned.
    Returns True/False when ready, None when required but missing."""
    if mode is False:
        return False
    if _git(workdir, "rev-parse", "--is-inside-work-tree").returncode == 0:
        return True
    if mode == "init" and _git(workdir, "init").returncode == 0:
        return True
    return None


def commit(workdir, message):
    """Commit every tracked change under workdir, excluding loop bookkeeping.
    Returns the commit hash, or None when the tree was already clean."""
    add = _git(workdir, "add", "-A", "--", ".", *EXCLUDE)
    if add.returncode != 0:
        raise FactoryError("git add failed: " + (add.stderr or "").strip()[:200])
    if _git(workdir, "diff", "--cached", "--quiet").returncode == 0:
        return None
    done = _git(workdir, "commit", "-m", message)
    if done.returncode != 0:
        raise FactoryError("git commit failed: " + (done.stderr or "").strip()[:200])
    return _git(workdir, "rev-parse", "HEAD").stdout.strip()


def diff_last_commit(workdir, cap=12000):
    """The committed diff a reviewer judges; capped so huge trees do not flood the prompt."""
    if _git(workdir, "rev-parse", "--verify", "HEAD").returncode != 0:
        return "(no commits yet)"
    out = _git(workdir, "show", "--format=", "HEAD")
    text = out.stdout or out.stderr or ""
    if len(text) > cap:
        text = text[:cap] + f"\n[{len(text) - cap} chars omitted]"
    return text


def make_cli_reviewer(argv, workdir, timeout=300):
    """A reviewer agent as a CLI command: goal + committed diff on stdin, must print
    ACCEPT (optionally notes) or REJECT: <concrete reason>. Anything else fails closed."""
    def review(goal, feedback):
        prompt = ("Review the last commit against the goal. Reply with ACCEPT if the diff "
                  "faithfully serves the goal, or REJECT: <concrete reason>.\nGOAL:\n" + goal +
                  "\n\nCOMMITTED DIFF:\n" + diff_last_commit(workdir))
        try:
            p = subprocess.run(argv, input=prompt, cwd=workdir, capture_output=True,
                               text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as ex:
            return False, f"reviewer unavailable: {type(ex).__name__}: {str(ex)[:160]}"
        text = (p.stdout or "").strip()
        if p.returncode != 0 or not text:
            return False, f"reviewer failed (exit {p.returncode}): {(p.stderr or '')[-200:]}"
        head, _, rest = text.partition("\n")
        if head.upper().startswith("ACCEPT"):
            inline = head[6:].lstrip(" :")
            return True, ((inline + "\n" + rest).strip() or "accepted")[:600]
        if head.upper().startswith("REJECT"):
            return False, (head[6:].lstrip(" :") + "\n" + rest).strip()[:600]
        return False, "unparseable reviewer reply (want ACCEPT or REJECT): " + text[:200]
    return review


def run_factory(defn, workdir, agent, review=None):
    """Run the closed loop. agent: callable(goal, feedback, workdir) or a CLI argv list.
    review: callable(goal, feedback) -> (accepted, notes); required when the definition
    sets review=true. Returns an honest status dict; DONE_VERIFIED is exit-code decided."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    if isinstance(defn, (str, Path)):
        defn = load(defn, workdir)
    dh = definition_hash(defn)
    emit(workdir, "factory", definition_sha256=dh, goal=defn["goal"][:200])
    repo = ensure_repo(workdir, defn["git"])
    if repo is None:
        emit(workdir, "status", status="FAILED_GIT_REQUIRED", iters=0)
        return {"status": "FAILED_GIT_REQUIRED", "mode": "factory", "definition_sha256": dh}
    if defn["review"] and review is None:
        emit(workdir, "status", status="FAILED_REVIEWER_REQUIRED", iters=0)
        return {"status": "FAILED_REVIEWER_REQUIRED", "mode": "factory", "definition_sha256": dh}
    if repo:
        commit(workdir, "rashi factory baseline")  # starting state is part of the audit trail
    spec = {"goal": defn["goal"], "workdir": str(workdir), "checks": defn["checks"],
            "protected": defn["protected"], "max_iters": defn["max_iters"],
            "max_seconds": defn["max_seconds"]}
    if repo:
        def _commit(iter_no, failed_ids):
            what = "checks pass" if not failed_ids else "checks failing: " + ",".join(failed_ids)
            commit(workdir, f"rashi factory iter {iter_no}: {what}")
        spec["git_commit"] = _commit
    if review is not None:
        spec["review"] = review
    if not callable(agent):
        agent = CliAgent(agent)
    status, log = run_loop(spec, agent)
    result = {"status": status, "mode": "factory", "definition_sha256": dh,
              "git": bool(repo), "iterations": len(log), "artifacts": defn["artifacts"]}
    if status == "DONE_VERIFIED" and defn["artifacts"]:
        # The artifacts gate: declared deliverables must exist and be plain files.
        missing = [rel for rel in defn["artifacts"]
                   if (workdir / rel).is_symlink() or not (workdir / rel).is_file()]
        if missing:
            result["status"] = "FAILED_ARTIFACT_MISSING"
            result["missing_artifacts"] = missing
            emit(workdir, "status", status="FAILED_ARTIFACT_MISSING", iters=len(log),
                 missing=missing)
    if log:
        result["last"] = log[-1]
    return result


def serve_preview(workdir, port=8766, host="127.0.0.1"):
    """Local-only static preview of what the factory produced. Loop bookkeeping files are
    visible too; it serves the caller's own workdir on their own machine and nothing leaves it."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(workdir))
    return http.server.ThreadingHTTPServer((host, port), handler)


STREAMLIT_ENTRY = "app.py"


def preview_kind(workdir):
    """A workdir with app.py is a live Streamlit app artifact (the Apache-2.0 framework
    E2B's artifacts clone uses for app output), not a static page."""
    if (Path(workdir) / STREAMLIT_ENTRY).is_file():
        return "streamlit"
    return "static"


def streamlit_preview(workdir, port=8766, host="127.0.0.1"):
    """Run the app.py artifact as a real local Streamlit app. Returns the Popen handle.
    Honest when the runtime is missing: no silent fallback to a static file."""
    entry = Path(workdir) / STREAMLIT_ENTRY
    if not entry.is_file():
        raise FactoryError(f"no {STREAMLIT_ENTRY} in {workdir}")
    try:
        import streamlit  # noqa: F401
    except ImportError:
        raise FactoryError("the artifact is a Streamlit app but streamlit is not installed "
                           "(pip install streamlit; Apache-2.0)")
    import sys
    return subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(entry),
                             "--server.port", str(port), "--server.address", host,
                             "--server.headless", "true", "--browser.gatherUsageStats", "false"],
                            cwd=workdir)
