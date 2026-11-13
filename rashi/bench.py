"""Benchmark: fixed build tasks, results recorded as data (his 2026-11-13 ownership pass:
reliability is proven with repeated numbers, not one demo).

run_bench(tasks, runner, out_path) runs each task through runner(task) -> dict with at
least {"status": ...}; every outcome (including runner crashes) is appended to out_path
as one JSON line. `runner` is injectable so tests use fakes: no network, no spend.
The live runner (one_press on a free model) is wired in rashi/__main__.py `bench`.
"""
import json
import time
from pathlib import Path


def load_tasks(path):
    tasks = json.loads(Path(path).read_text())
    assert all(t.get("id") and t.get("goal") and isinstance(t.get("checks"), list) for t in tasks), \
        "each benchmark task needs id, goal and checks"
    for t in tasks:  # optional fields, validated when present
        assert isinstance(t.get("seed", {}), dict), f"{t['id']}: seed must be {{path: content}}"
        assert isinstance(t.get("protected", []), list), f"{t['id']}: protected must be a list"
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
        with open(out_path, "a") as f:
            f.write(json.dumps(row) + "\n")
    done = sum(r["status"] == "DONE_VERIFIED" for r in rows)
    return {"n": len(rows), "done_verified": done, "pass_rate": round(done / len(rows), 3) if rows else 0,
            "rows": rows}
