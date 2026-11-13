import json
from pathlib import Path
from rashi.pipeline import run_pipeline


def llm(system, user):
    if "fresh reviewer" in system:
        return '{"findings":[]}'
    return "Goal\nChecks\n- `test -f out.txt`\n"


def test_end_to_end_done_and_gates(tmp_path):
    agent = lambda g, f, wd: Path(wd, "out.txt").write_text("x")
    r = run_pipeline("write out", str(tmp_path), llm, agent, lambda s, f: True)
    assert r["status"] == "DONE_VERIFIED" and r["review"] == []
    r2 = run_pipeline("write out", str(tmp_path / "n"), llm, agent, lambda s, f: False)
    assert r2["status"] == "SPEC_NOT_APPROVED"


def test_out_of_scope_edits_are_flagged(tmp_path):
    def agent(g, f, wd):
        Path(wd, "out.txt").write_text("x")
        Path(wd, "sneaky.txt").write_text("x")
    r = run_pipeline("write out", str(tmp_path), llm, agent, lambda s, f: True)
    assert r["status"] == "DONE_VERIFIED"
    assert r["scope"]["out_of_scope"] == ["sneaky.txt"]


def test_event_log_records_route_iter_status(tmp_path):
    agent = lambda g, f, wd: Path(wd, "out.txt").write_text("x")
    run_pipeline("write out", str(tmp_path), llm, agent, lambda s, f: True)
    kinds = [json.loads(l)["kind"] for l in Path(tmp_path, "events.jsonl").read_text().splitlines()]
    kinds = [k for k in kinds if not k.startswith("span")]  # span events are tracing, not run events
    assert kinds == ["route", "iter", "status"]


def test_failing_check_never_done(tmp_path):
    r = run_pipeline("g", str(tmp_path), llm, lambda g, f, wd: None, lambda s, f: True, max_iters=2)
    assert r["status"] == "STOPPED_MAX_ITERS"


def test_pipeline_emits_drift_event(tmp_path):
    """After the loop, the drift report lands in the result and (when drifted) events.jsonl."""
    import json as _json
    (tmp_path / "ok.py").write_text("")
    def llm(system, user):
        if "fresh reviewer" in system:
            return '{"findings":[]}'
        return "Goal\nFiles\n- `ok.py`\n- `ghost.py`\nChecks\n- `test -f ok.py`\n"
    r = run_pipeline("g", str(tmp_path), llm, lambda g, f, wd: None, lambda s, f: True)
    assert r["drift"]["drifted"] and "ghost.py" in r["drift"]["missing_paths"]
    events = [_json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(e.get("kind") == "drift" for e in events)


def test_spans_wrap_run_phases(tmp_path):
    """B10: span_start/span_end events with durations and parent links land in events.jsonl."""
    import json as _json
    (tmp_path / "ok.py").write_text("")
    def llm(system, user):
        return '{"findings":[]}' if "fresh reviewer" in system else "Checks\n- `test -f ok.py`\n"
    run_pipeline("g", str(tmp_path), llm, lambda g, f, wd: None, lambda s, f: True)
    events = [_json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    starts = {e["span"]: e for e in events if e.get("kind") == "span_start"}
    ends = {e["span"]: e for e in events if e.get("kind") == "span_end"}
    assert set(starts) == set(ends) and {"run", "route", "spec_gate", "run_loop"} <= {e["name"] for e in starts.values()}
    assert all("duration_ms" in e for e in ends.values())
    run_id = next(s for s, e in starts.items() if e["name"] == "run")
    assert starts[next(s for s, e in starts.items() if e["name"] == "spec_gate")]["parent"] == run_id
