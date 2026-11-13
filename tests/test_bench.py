import json

from rashi import bench


def test_load_tasks_validates_shape(tmp_path):
    tasks = bench.load_tasks("benchmarks/tasks.json")
    assert len(tasks) == 4 and all(t["checks"] for t in tasks)
    guard = next(t for t in tasks if t["id"] == "bench-guard")
    assert set(guard["seed"]) == set(guard["protected"])  # every seeded file is guarded
    bad_shape = tmp_path / "badseed.json"
    bad_shape.write_text(json.dumps([{"id": "x", "goal": "g", "checks": ["true"], "seed": []}]))
    try:
        bench.load_tasks(bad_shape)
        assert False, "seed must be a {path: content} dict"
    except AssertionError:
        pass
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"id": "x"}]))
    try:
        bench.load_tasks(bad)
        assert False, "shape check should reject a task without goal/checks"
    except AssertionError:
        pass


def test_run_bench_records_every_outcome(tmp_path):
    out = tmp_path / "bench.jsonl"
    tasks = [{"id": "a", "goal": "g", "checks": ["true"]},
             {"id": "b", "goal": "g", "checks": ["true"]},
             {"id": "c", "goal": "g", "checks": ["true"]}]

    def runner(t):
        if t["id"] == "a":
            return {"status": "DONE_VERIFIED", "iterations": 2}
        if t["id"] == "b":
            return {"status": "FAILED", "iterations": 6}
        raise RuntimeError("boom")

    summary = bench.run_bench(tasks, runner, out)
    assert summary["n"] == 3 and summary["done_verified"] == 1
    assert summary["pass_rate"] == round(1 / 3, 3)
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert [r["status"] for r in rows] == ["DONE_VERIFIED", "FAILED", "RUNNER_CRASH"]
    assert rows[2]["error"].startswith("RuntimeError: boom")
    assert all(r["wall_s"] is not None and r["ts"] for r in rows)


def test_run_bench_appends_across_runs(tmp_path):
    out = tmp_path / "bench.jsonl"
    t = [{"id": "a", "goal": "g", "checks": ["true"]}]
    bench.run_bench(t, lambda _: {"status": "DONE_VERIFIED"}, out)
    bench.run_bench(t, lambda _: {"status": "FAILED"}, out)
    assert len(out.read_text().splitlines()) == 2  # history is never overwritten
