"""Verified loop: exit codes of the checks decide DONE. Model text never does.

spec (dict or JSON file):
  goal, checks:[{id,cmd}], protected:[paths], max_iters, max_seconds, workdir
An `agent` is any callable agent(goal, feedback, workdir) -> None that edits files.
"""
import hashlib, json, os, subprocess, time
from pathlib import Path


def run_cmd(cmd, cwd, timeout=300, spill_dir=None):
    """Spill (pattern from dsh spill-policy): output over the cap lands in a private file and the
    check result keeps head+tail plus the locator, instead of silently amputating the middle."""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
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


def snapshot(workdir):
    """{relative path: sha256} for every file, used to see exactly what an agent touched."""
    out = {}
    for fp in sorted(Path(workdir).rglob("*")):
        if fp.is_file() and "__pycache__" not in fp.parts and ".git" not in fp.parts:
            out[str(fp.relative_to(workdir))] = hashlib.sha256(fp.read_bytes()).hexdigest()
    return out


def changed_since(before, workdir):
    after = snapshot(workdir)
    return {"changed": sorted(p for p in after if before.get(p) != after[p]),
            "removed": sorted(p for p in before if p not in after)}


def run_loop(spec, agent, state_path=None):
    wd = spec.get("workdir", ".")
    Path(wd).mkdir(parents=True, exist_ok=True)  # the loop owns its workdir; never crash on a missing one
    state_path = state_path or os.path.join(wd, "PROGRESS.json")
    protected = spec.get("protected", [])
    base = digest(wd, protected)
    absent = [p for p in protected if not (Path(wd) / p).exists()]
    if absent:  # an absent protected path silently protects nothing; say so in the event log
        emit(wd, "warn", what="protected paths absent", paths=absent)
    start, feedback, log, status = time.time(), "", [], "STOPPED_MAX_ITERS"
    prev_failed = prev_tree = None
    for i in range(1, spec.get("max_iters", 6) + 1):
        if time.time() - start > spec.get("max_seconds", 900):
            status = "STOPPED_TIME"; break
        err = None
        try:
            agent(spec["goal"], feedback, wd)
        except Exception as ex:  # agent failure is recorded, loop continues
            err = f"{type(ex).__name__}: {str(ex)[:200]}"
        if digest(wd, protected) != base:
            status = "FAILED_TAMPERED_PROTECTED_FILES"; break
        results = [(c["id"],) + run_cmd(c["cmd"], wd, timeout=spec.get("check_timeout", 300),
                                        spill_dir=Path(wd) / ".spill")
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
        # Repeat guard (pattern from dsh repeat-tool-reminder): an iteration that changed nothing
        # and failed the same checks as the one before is looping, not working - say so, advisory.
        # Runtime files (state, events, spill, replay tape) are excluded or the tree always changes.
        now = {str(fp.relative_to(wd)): hashlib.sha256(fp.read_bytes()).hexdigest()
               for fp in sorted(Path(wd).rglob("*")) if fp.is_file()
               and "__pycache__" not in fp.parts and ".git" not in fp.parts
               and fp.name not in ("PROGRESS.json", "events.jsonl", ".replay.jsonl")
               and ".spill" not in fp.parts}
        if failed == prev_failed and now == prev_tree:
            emit(wd, "warn", what="no progress: same failures, no file changes", iter=i)
        prev_failed, prev_tree = failed, now
        feedback = "\n".join(f"{r[0]} exit {r[1]}: {r[2]}" for r in failed)
    Path(state_path).write_text(json.dumps({"status": status, "goal": spec["goal"], "log": log}, indent=1))
    emit(wd, "status", status=status, iters=len(log))
    return status, log
