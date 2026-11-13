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
        if fp.is_file() and not fp.is_symlink() and not any(part in SKIP_DIRS for part in fp.parts):
            h = hashlib.sha256()
            with open(fp,"rb") as stream:
                for chunk in iter(lambda:stream.read(65536), b""):
                    h.update(chunk)
            out[str(fp.relative_to(workdir))] = h.hexdigest()
    return out


def changed_since(before, workdir):
    after = snapshot(workdir)
    return {"changed": sorted(p for p in after if before.get(p) != after[p]),
            "removed": sorted(p for p in before if p not in after)}


def _inside(root, rel):
    """Cooperative rollback guard: reject traversal and symlink components, including leaf.
    This is not race-proof against a concurrently malicious process; agents must be stopped."""
    root = Path(root).resolve()
    relpath = Path(rel)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise ValueError("unsafe rollback path")
    target = root
    for part in relpath.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("symlink in rollback path")
    return target


def stash_in(workdir, max_bytes=1_000_000, max_total=8_000_000):
    """Bound pre-step bytes before reading; exclude runtime logs/state from undo."""
    before = {rel:sha for rel,sha in snapshot(workdir).items()
              if rel not in ("PROGRESS.json", "events.jsonl", ".replay.jsonl", ".spend.json")}
    pending, total = {}, 0
    for rel in before:
        try:
            fp = _inside(workdir,rel)
            size = fp.stat().st_size
            if size <= max_bytes and total + size <= max_total:
                with open(fp,"rb") as stream:
                    content = stream.read(max_bytes + 1)
                if len(content) <= max_bytes:
                    pending[rel] = (content,fp.stat().st_mode & 0o777)
                    total += len(content)
        except (OSError, ValueError):
            pass
    stash.pending[str(workdir)] = pending
    return before


def stash(workdir, before, n, max_bytes=1_000_000, keep=3):
    """Record modified/deleted pre-step bytes and additions. Bounded capture, last 3 stashes."""
    after = {rel:sha for rel,sha in snapshot(workdir).items()
             if rel not in ("PROGRESS.json", "events.jsonl", ".replay.jsonl", ".spend.json")}
    added = sorted(set(after)-set(before))
    changed = sorted(p for p in after if p in before and before[p] != after[p])
    removed = sorted(set(before)-set(after))
    pending = stash.pending.pop(str(workdir), {})
    if not added and not changed and not removed:
        return None
    root = _inside(workdir,".rashi/rollback")
    root.mkdir(parents=True, exist_ok=True)
    dest = _inside(root,str(n))
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    dest.mkdir()
    uncopied, modes = [], {}
    for rel in changed + removed:
        value = pending.get(rel)
        if value is None:
            uncopied.append(rel); continue
        content, mode = value
        fp = _inside(dest,"files/"+rel)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(content)
        modes[rel] = mode
    manifest = {"added":added,"changed":changed,"removed":removed,"uncopied":uncopied,"modes":modes}
    (dest/"manifest.json").write_text(json.dumps(manifest))
    import shutil
    for old in sorted((d for d in root.iterdir() if d.is_dir() and not d.is_symlink()
                       and d.name.isdigit()),key=lambda d:int(d.name))[:-keep]:
        shutil.rmtree(old)
    return manifest


stash.pending = {}


def rollback(workdir, n):
    """Undo a stopped cooperative agent step; unsafe or uncaptured paths are explicit failures."""
    dest = _inside(workdir,".rashi/rollback/"+str(n))
    manifest = json.loads(_inside(dest,"manifest.json").read_text())
    deleted, restored, missing = [], [], set(manifest["uncopied"])
    for rel in manifest["added"]:
        try:
            fp = _inside(workdir,rel)
            if fp.is_file():
                fp.unlink(); deleted.append(rel)
        except (OSError,ValueError):
            missing.add(rel)
    for rel in manifest["changed"] + manifest.get("removed",[]):
        try:
            fp = _inside(workdir,rel)
            src = _inside(dest,"files/"+rel)
            if not src.is_file():
                missing.add(rel); continue
            fp.parent.mkdir(parents=True,exist_ok=True)
            fp.write_bytes(src.read_bytes())
            fp.chmod(manifest.get("modes",{}).get(rel,0o600))
            restored.append(rel)
        except (OSError,ValueError):
            missing.add(rel)
    return {"restored":restored,"deleted":deleted,"unrestorable":sorted(missing)}


def run_loop(spec, agent, state_path=None):
    wd = spec.get("workdir", ".")
    Path(wd).mkdir(parents=True, exist_ok=True)  # the loop owns its workdir; never crash on a missing one
    state_path = state_path or os.path.join(wd, "PROGRESS.json")
    log = []
    checks = spec.get("checks")
    if (not isinstance(checks,list) or not checks or
        any(not isinstance(c,dict) or not isinstance(c.get("cmd"),str) or not c["cmd"].strip()
            or not isinstance(c.get("id"),str) for c in checks) or
        len({c["id"] for c in checks}) != len(checks)):
        emit(wd,"status",status="FAILED_INVALID_CHECKS",iters=0)
        return "FAILED_INVALID_CHECKS", []
    identity = hashlib.sha256(json.dumps({"goal":spec["goal"],"checks":checks,
                                        "protected":spec.get("protected",[])},sort_keys=True).encode()).hexdigest()
    feedback = ""
    protected_start = digest(wd,spec.get("protected",[]))
    if spec.get("resume", True) and Path(state_path).is_file():
        try:
            prev = json.loads(Path(state_path).read_text())
            if (isinstance(prev,dict) and prev.get("goal") == spec["goal"] and
                prev.get("status") in ("RUNNING","STOPPED_MAX_ITERS","STOPPED_TIME")):
                if prev.get("spec_id") != identity or prev.get("protected_digest") != protected_start:
                    emit(wd,"status",status="FAILED_RESUME_IDENTITY_MISMATCH",iters=0)
                    return "FAILED_RESUME_IDENTITY_MISMATCH", []
                old_log = prev.get("log",[])
                if not isinstance(old_log,list) or any(not isinstance(r,dict) for r in old_log):
                    raise ValueError("invalid resume log")
                log = old_log
                feedback = prev.get("feedback", "")
                if log:
                    emit(wd, "resumed", iters_done=len(log))
        except (ValueError,OSError,TypeError):
            emit(wd,"warn",what="invalid resume state; starting fresh")

    def save_state(status):
        payload = {"status":status,"goal":spec["goal"],"spec_id":identity,
                   "protected_digest":protected_start,"feedback":feedback,"log":log}
        dest = Path(state_path)
        # Replace state atomically so interruption cannot leave a partial JSON document.
        temporary = dest.with_name(dest.name+".tmp")
        temporary.write_text(json.dumps(payload,indent=1))
        temporary.replace(dest)
    from . import sandbox as _sandbox
    use_sandbox = _sandbox.requested(spec)
    sandbox_argv = None
    if use_sandbox:
        if _sandbox.available():
            sandbox_argv = _sandbox.wrap_argv(wd, net=bool(spec.get("sandbox_net")))
        else:
            status = "FAILED_SANDBOX_UNAVAILABLE"
            emit(wd, "status", status=status, iters=0)
            save_state(status)
            return status, log
    protected = spec.get("protected", [])
    base = digest(wd, protected)
    absent = [p for p in protected if not (Path(wd) / p).exists()]
    if absent:  # an absent protected path silently protects nothing; say so in the event log
        emit(wd, "warn", what="protected paths absent", paths=absent)
    start, status = time.time(), "STOPPED_MAX_ITERS"
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
        save_state("FAILED_TAMPERED_PROTECTED_FILES")
        emit(wd, "status", status="FAILED_TAMPERED_PROTECTED_FILES", iters=0)
        return "FAILED_TAMPERED_PROTECTED_FILES", log
    baseline_feedback = "\n".join(f"{r[0]} exit {r[1]}: {r[2]}" for r in prev_failed)
    feedback = (feedback + "\nCurrent checks:\n" + baseline_feedback).strip()
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
        try:
            stashed = stash(wd, before, i)
        except (ValueError,OSError) as ex:
            emit(wd,"warn",what="rollback storage unsafe or unavailable",detail=str(ex)[:160])
            status = "FAILED_ROLLBACK_STORAGE"; break
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
        save_state("RUNNING")
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
            if rb["unrestorable"]:
                status = "FAILED_ROLLBACK_INCOMPLETE"; break
            restored_results = [(c["id"],) + run_cmd(c["cmd"], wd,
                                timeout=spec.get("check_timeout",300),
                                spill_dir=Path(wd)/".spill", sandbox_argv=sandbox_argv)
                                for c in spec["checks"]]
            prev_failed = [r for r in restored_results if r[1] != 0]
        # Repeat guard (pattern from dsh repeat-tool-reminder): an iteration that changed nothing
        # and failed the same checks as the one before is looping, not working - say so, advisory.
        # Runtime files (state, events, spill, replay tape) are excluded or the tree always changes.
        now = {rel:sha for rel,sha in snapshot(wd).items()
               if rel not in ("PROGRESS.json","events.jsonl",".replay.jsonl")}
        eff_failed = prev_failed if rolled_back else failed
        if eff_failed == prev_failed and now == prev_tree:
            emit(wd, "warn", what="no progress: same failures, no file changes", iter=i)
        prev_failed, prev_tree = eff_failed, now
        feedback = "\n".join(f"{r[0]} exit {r[1]}: {r[2]}" for r in failed)
        if rolled_back:
            feedback = (f"Your last change was ROLLED BACK: it broke previously-passing checks "
                        f"{regressed}. Do not re-apply it; find a different approach.\n" + feedback)
        save_state("RUNNING")
    save_state(status)
    emit(wd, "status", status=status, iters=len(log))
    _memory.remember(wd, "done" if status == "DONE_VERIFIED" else "note",
                     f"goal '{spec['goal'][:120]}' ended {status} after {len(log)} iters")
    return status, log
