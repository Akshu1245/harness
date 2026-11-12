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


def test_failing_check_never_done(tmp_path):
    r = run_pipeline("g", str(tmp_path), llm, lambda g, f, wd: None, lambda s, f: True, max_iters=2)
    assert r["status"] == "STOPPED_MAX_ITERS"
