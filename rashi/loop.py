"""Verified loop: exit codes of the checks decide DONE. Model text never does.

spec (dict or JSON file):
  goal, checks:[{id,cmd}], protected:[paths], max_iters, max_seconds, workdir
An `agent` is any callable agent(goal, feedback, workdir) -> None that edits files.

Resume (B6): a PROGRESS.json with the same goal and an unfinished status continues where it
stopped (spec["resume"]=False disables). Rollback (B5): an iteration that leaves MORE checks
failing than the previous one is undone from the per-step stash in .rashi/rollback/ and logged.
"""
import hashlib, json, os, subprocess, time
from pathlib import Path

from . import memory as _memory


def run_cmd(cmd, cwd, timeout=300, spill_dir=None, sandbox_argv=None):
    """sandbox_argv: a bwrap prefix (rashi.sandbox.wrap_argv) to run the check inside."""
    if sandbox_argv:
        cmd = sandbox_argv + ["sh", "-c", cmd]  # argv form, no extra shell parsing
    """Spill (pattern from dsh spill-policy): output over the cap lands in a private file and the
    check result keeps head+tail plus the locator, instead of silently amputating the middle."""
    try:
        argv = cmd if isinstance(cmd, list) else None
        p = subprocess.run(argv or cmd, shell=argv is None, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd)
        out = p.stdout + p.stderr
        if len(out) > 2000 and spill_dir is not None:
            spill_dir = Path(spill_dir)
            spill_dir.mkdir(parents=True, exist_ok=True)
            name = spill_dir / f"{len(list(spill_dir.iterdir())) + 1}.log"
            name.write_text(out)
            out = out[:1000] + f"\n[{len(out) - 2000} chars omitted; full output: {name}]\n" + out[-1000:]
        return p.returncode, out[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as ex:  # missing workdir, unspawnable shell: a failed check, not a loop crash
        return 2, f"spawn error: {ex}"


def digest(workdir, paths):
    h = hashlib.sha256()
    for rel in paths:
        base = Path(workdir) / rel
        files = sorted(base.rglob("*")) if base.is_dir() else [base]
        for fp in files:
            if fp.is_file() and "__pycache__" not in fp.parts:
                h.update(str(fp.relative_to(workdir)).encode()); h.update(fp.read_bytes())
    return h.hexdigest()


def emit(workdir, kind, **fields):
    """Append one event to events.jsonl: the real event log the war room renders."""
    with open(Path(workdir) / "events.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "kind": kind, **fields}) + "\n")


SKIP_DIRS = ("__pycache__", ".git", ".rashi", ".spill")


def snapshot(workdir):
    """{relative path: sha256} for every file, used to see exactly what an agent touched.
    Loop bookkeeping dirs (.rashi rollback stash, .spill output) are not agent work."""
    out = {}
    for fp in sorted(Path(workdir).rglob("*")):
        if fp.is_file() and not any(part in SKIP_DIRS for part in fp.parts):
            out[str(fp.relative_to(workdir))] = hashlib.sha256(fp.read_bytes()).hexdigest()
    return out


def changed_since(before, workdir):
    after = snapshot(workdir)
    return {"changed": sorted(p for p in after if before.get(p) != after[p]),
            "removed": sorted(p for p in before if p not in after)}


def stash(workdir, before, n, max_bytes=1_000_000, keep=3):
    """Per-step rollback store (B5): after agent step n, record what changed and keep the
    pre-step bytes (captured by stash_in) under .rashi/rollback/<n>/. Files over max_bytes are
    recorded as uncopied, never silently half-restored. Only the last `keep` stashes are kept."""
    after = snapshot(workdir)
    added = sorted(p for p in after if p not in before)
    changed = sorted(p for p in after if p in before and before[p] != after[p])
    if not added and not changed:
        return None
    root = Path(workdir) / ".rashi" / "rollback"
    dest = root / str(n)
    dest.mkdir(parents=True, exist_ok=True)
    big = []
    for rel, content in stash.pending.pop(str(workdir), {}).items():
        if rel not in changed:
            continue
        if len(content) > max_bytes:
            big.append(rel); continue
        fp = dest / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(content)
    (dest / "manifest.json").write_text(json.dumps({"added": added, "changed": changed, "uncopied": big}))
    for old_dir in sorted((d for d in root.iterdir() if d.is_dir() and d.name.isdigit()), key=lambda d: int(d.name))[:-keep]:
        for fp in sorted(old_dir.rglob("*"), reverse=True):
            fp.unlink() if fp.is_file() else fp.rmdir()
        old_dir.rmdir()
    return {"added": added, "changed": changed, "uncopied": big}


stash.pending = {}  # workdir -> {rel path: pre-step bytes}, filled by stash_in


def stash_in(workdir):
    """Capture pre-step content so a later regression can be undone."""
    before = snapshot(workdir)
    pending = {}
    for rel in before:
        try:
            pending[rel] = (Path(workdir) / rel).read_bytes()
        except OSError:
            pass
    stash.pending[str(workdir)] = pending
    return before


def rollback(workdir, n):
    """Undo agent step n: restore stashed pre-step content, delete files the step added."""
    dest = Path(workdir) / ".rashi" / "rollback" / str(n)
    manifest = json.loads((dest / "manifest.json").read_text())
    deleted = []
    for rel in manifest["added"]:
        fp = Path(workdir) / rel
        if fp.is_file():
            fp.unlink(); deleted.append(rel)
    restored, missing = [], []
    for rel in manifest["changed"]:
        src = dest / rel
        if src.is_file():
            (Path(workdir) / rel).write_bytes(src.read_bytes()); restored.append(rel)
        else:
            missing.append(rel)
    return {"restored": restored, "deleted": deleted, "unrestorable": manifest["uncopied"] + missing}


def run_loop(spec, agent, state_path=None):
    wd = spec.get("workdir", ".")
    Path(wd).mkdir(parents=True, exist_ok=True)  # the loop owns its workdir; never crash on a missing one
    state_path = state_path or os.path.join(wd, "PROGRESS.json")
    log = []
    if spec.get("resume", True) and Path(state_path).is_file():  # resume (B6): continue an interrupted run
        try:
            prev = json.loads(Path(state_path).read_text())
            if prev.get("goal") == spec["goal"] and prev.get("status") not in (None, "DONE_VERIFIED"):
                log = list(prev.get("log", []))
                if log:
                    emit(wd, "resumed", iters_done=len(log))
        except (ValueError, OSError):
            pass  # a corrupt state file starts a fresh run, never a crash
    from . import sandbox as _sandbox
    use_sandbox = _sandbox.requested(spec)
    sandbox_argv = None
    if use_sandbox:
        if _sandbox.available():
            sandbox_argv = _sandbox.wrap_argv(wd, net=bool(spec.get("sandbox_net")))
        else:
            emit(wd, "warn", what="sandbox requested but bwrap not available; checks run unsandboxed")
    protected = spec.get("protected", [])
    base = digest(wd, protected)
    absent = [p for p in protected if not (Path(wd) / p).exists()]
    if absent:  # an absent protected path silently protects nothing; say so in the event log
        emit(wd, "warn", what="protected paths absent", paths=absent)
    start, feedback, status = time.time(), "", "STOPPED_MAX_ITERS"
    # Baseline: check the starting tree once. Regression is judged against the last check
    # result BEFORE each agent step, so the first step needs a baseline to be judged against.
    # On a resumed run the baseline is just re-measured on the current tree.
    prev_failed = [(c["id"],) + run_cmd(c["cmd"], wd, timeout=spec.get("check_timeout", 300),
                                        spill_dir=Path(wd) / ".spill", sandbox_argv=sandbox_argv)
                   for c in spec["checks"]]
    prev_failed = [r for r in prev_failed if r[1] != 0]
    if digest(wd, protected) != base:  # the baseline itself ran a tampering check: fail closed
        log.append({"iter": 0, "failed": [r[0] for r in prev_failed], "agent_error": None,
                    "tampered_by": "checks"})
        emit(wd, "iter", iter=0, failed=[r[0] for r in prev_failed], tampered_by="checks")
        Path(state_path).write_text(json.dumps(
            {"status": "FAILED_TAMPERED_PROTECTED_FILES", "goal": spec["goal"], "log": log}, indent=1))
        emit(wd, "status", status="FAILED_TAMPERED_PROTECTED_FILES", iters=0)
        return "FAILED_TAMPERED_PROTECTED_FILES", log
    prev_tree = None
    for i in range(len(log) + 1, spec.get("max_iters", 6) + 1):
        if time.time() - start > spec.get("max_seconds", 900):
            status = "STOPPED_TIME"; break
        err = None
        before = stash_in(wd)
        try:
            agent(spec["goal"], feedback, wd)
        except Exception as ex:  # agent failure is recorded, loop continues
            err = f"{type(ex).__name__}: {str(ex)[:200]}"
        stashed = stash(wd, before, i)
        if digest(wd, protected) != base:
            status = "FAILED_TAMPERED_PROTECTED_FILES"; break
        results = [(c["id"],) + run_cmd(c["cmd"], wd, timeout=spec.get("check_timeout", 300),
                                        spill_dir=Path(wd) / ".spill", sandbox_argv=sandbox_argv)
                   for c in spec["checks"]]
        failed = [r for r in results if r[1] != 0]
        if digest(wd, protected) != base:  # a check command itself tampered with protected files
            log.append({"iter": i, "failed": [r[0] for r in failed], "agent_error": err, "tampered_by": "checks"})
            emit(wd, "iter", iter=i, failed=[r[0] for r in failed], agent_error=err, tampered_by="checks")
            status = "FAILED_TAMPERED_PROTECTED_FILES"; break
        log.append({"iter": i, "failed": [r[0] for r in failed], "agent_error": err})
        emit(wd, "iter", iter=i, failed=[r[0] for r in failed], agent_error=err)
        Path(state_path).write_text(json.dumps({"status": "RUNNING", "goal": spec["goal"], "log": log}, indent=1))
        if not failed:
            status = "DONE_VERIFIED"; break
        # Regression rollback (B5): a check that passed before this agent step and fails now means
        # the step made things worse - undo it and keep working from the last better tree.
        rolled_back = False
        regressed = sorted(set(r[0] for r in failed) - set(r[0] for r in prev_failed))
        if regressed and stashed:
            rb = rollback(wd, i)
            rolled_back = True
            emit(wd, "rollback", iter=i, regressed=regressed, restored=rb["restored"],
                 deleted=rb["deleted"], unrestorable=rb["unrestorable"])
            _memory.remember(wd, "rollback", f"iter {i}: rolled back a step that broke {regressed}")
        # Repeat guard (pattern from dsh repeat-tool-reminder): an iteration that changed nothing
        # and failed the same checks as the one before is looping, not working - say so, advisory.
        # Runtime files (state, events, spill, replay tape) are excluded or the tree always changes.
        now = {str(fp.relative_to(wd)): hashlib.sha256(fp.read_bytes()).hexdigest()
               for fp in sorted(Path(wd).rglob("*")) if fp.is_file()
               and not any(part in SKIP_DIRS for part in fp.parts)
               and fp.name not in ("PROGRESS.json", "events.jsonl", ".replay.jsonl")}
        eff_failed = prev_failed if rolled_back else failed
        if eff_failed == prev_failed and now == prev_tree:
            emit(wd, "warn", what="no progress: same failures, no file changes", iter=i)
        prev_failed, prev_tree = eff_failed, now
        feedback = "\n".join(f"{r[0]} exit {r[1]}: {r[2]}" for r in failed)
        if rolled_back:
            feedback = (f"Your last change was ROLLED BACK: it broke previously-passing checks "
                        f"{regressed}. Do not re-apply it; find a different approach.\n" + feedback)
    Path(state_path).write_text(json.dumps({"status": status, "goal": spec["goal"], "log": log}, indent=1))
    emit(wd, "status", status=status, iters=len(log))
    _memory.remember(wd, "done" if status == "DONE_VERIFIED" else "note",
                     f"goal '{spec['goal'][:120]}' ended {status} after {len(log)} iters")
    return status, log
