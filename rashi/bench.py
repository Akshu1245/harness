"""Benchmark: fixed build tasks, results recorded as data (his 2026-11-13 ownership pass:
reliability is proven with repeated numbers, not one demo).

run_bench(tasks, runner, out_path) runs each task through runner(task) -> dict with at
least {"status": ...}; every outcome (including runner crashes) is appended to out_path
as one JSON line. `runner` is injectable so tests use fakes: no network, no spend.
The live runner (one_press on a free model) is wired in rashi/__main__.py `bench`.
"""
import json
import subprocess
import time
from pathlib import Path


def killed(task, mutant, workdir):
    """Write a mutant (a wrong-but-plausible solution) into the seeded workdir and
    return True when at least one check FAILS on it. TestSuiteBench's mutation score,
    shrunk to bench size: a check suite that accepts the mutant is too weak to gate
    DONE (PAIN_POINTS pain 17/23). Mutants live in the task as {path, content}."""
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    for rel, content in task.get("seed", {}).items():
        (wd / rel).write_text(content)
    for rel, content in mutant["files"].items():
        (wd / rel).write_text(content)
    steps = task.get("steps") or [{"checks": task.get("checks", [])}]
    checks = [c for s in steps for c in s["checks"]]
    return any(subprocess.run(c, shell=True, cwd=wd, capture_output=True, timeout=30).returncode != 0
               for c in checks)


def falsifiable(task, workdir):
    """Seed the task into workdir and return the checks that still FAIL before any
    work. A task whose checks all pass on the untouched seed proves nothing: DONE
    would be granted for free (TestSuiteBench's lesson - valid checks can still be
    weak). Guard checks that re-verify the seed (e.g. bench-guard's helpers test)
    pass pre-work by design, so the requirement is: at least one check must fail."""
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    for rel, content in task.get("seed", {}).items():
        (wd / rel).write_text(content)
    steps = task.get("steps") or [{"checks": task.get("checks", [])}]
    checks = [c for s in steps for c in s["checks"]]
    return [c for c in checks
            if subprocess.run(c, shell=True, cwd=wd, capture_output=True, timeout=30).returncode != 0]


def load_tasks(path):
    tasks = json.loads(Path(path).read_text())
    for t in tasks:
        assert t.get("id"), "each benchmark task needs an id"
        steps = t.get("steps") or [{"goal": t.get("goal"), "checks": t.get("checks")}]
        assert all(s.get("goal") and isinstance(s.get("checks"), list) for s in steps), \
            f"{t['id']}: each step needs goal and checks"
        assert isinstance(t.get("seed", {}), dict), f"{t['id']}: seed must be {{path: content}}"
        assert isinstance(t.get("protected", []), list), f"{t['id']}: protected must be a list"
        assert all(isinstance(m.get("files"), dict) for m in t.get("mutants", [])), \
            f"{t['id']}: each mutant needs {{files: {{path: content}}}}"
    return tasks


def run_bench(tasks, runner, out_path):
    rows = []
    for t in tasks:
        start = time.time()
        try:
            res = runner(t) or {}
            row = {"task": t["id"], "status": res.get("status", "UNKNOWN"),
                   "iterations": res.get("iterations"), "error": None}
        except Exception as ex:  # a crashed run is a recorded failure, never a hidden one
            row = {"task": t["id"], "status": "RUNNER_CRASH", "iterations": None,
                   "error": f"{type(ex).__name__}: {str(ex)[:160]}"}
        row["wall_s"] = round(time.time() - start, 1)
        row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        rows.append(row)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(json.dumps(row) + "\n")
    done = sum(r["status"] == "DONE_VERIFIED" for r in rows)
    return {"n": len(rows), "done_verified": done, "pass_rate": round(done / len(rows), 3) if rows else 0,
            "rows": rows}
