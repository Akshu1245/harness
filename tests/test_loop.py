import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from rashi.loop import run_loop
from rashi.llm_agent import parse_files, safe_write, make_agent

def mk(tmp, check="test -f out.txt"):
    (tmp / "spec_guard.txt").write_text("locked")
    return {"goal": "g", "workdir": str(tmp), "protected": ["spec_guard.txt"], "max_iters": 3,
            "checks": [{"id": "C1", "cmd": check}]}

def test_done_only_when_check_passes(tmp_path):
    n = {"i": 0}
    def agent(goal, fb, wd):
        n["i"] += 1
        if n["i"] == 2: (pathlib.Path(wd) / "out.txt").write_text("x")
    st, log = run_loop(mk(tmp_path), agent)
    assert st == "DONE_VERIFIED" and len(log) == 2 and log[0]["failed"] == ["C1"]

def test_model_claim_of_done_is_ignored(tmp_path):
    st, log = run_loop(mk(tmp_path), lambda g, f, w: print("ALL DONE, everything is ready"))
    assert st == "STOPPED_MAX_ITERS" and len(log) == 3

def test_tampering_with_protected_file_fails(tmp_path):
    spec = mk(tmp_path, check="true")
    st, _ = run_loop(spec, lambda g, f, w: (pathlib.Path(w) / "spec_guard.txt").write_text("hacked"))
    assert st == "FAILED_TAMPERED_PROTECTED_FILES"

def test_agent_exception_recorded_and_loop_continues(tmp_path):
    def agent(g, f, w): raise RuntimeError("gateway 500")
    st, log = run_loop(mk(tmp_path), agent)
    assert st == "STOPPED_MAX_ITERS" and "RuntimeError" in log[0]["agent_error"]

def test_progress_file_written(tmp_path):
    run_loop(mk(tmp_path), lambda g, f, w: None)
    assert json.loads((tmp_path / "PROGRESS.json").read_text())["status"] == "STOPPED_MAX_ITERS"

def test_parse_files():
    t = "FILE: a/b.py\n```python\nx=1\n```\nFILE: c.py\n```\ny=2\n```"
    assert parse_files(t) == [("a/b.py", "x=1\n"), ("c.py", "y=2\n")]
    assert parse_files("I'm sorry, I can't") == []

def test_path_traversal_and_protected_blocked(tmp_path):
    with pytest.raises(ValueError): safe_write(tmp_path, "../evil.py", "x")
    with pytest.raises(ValueError): safe_write(tmp_path, "/etc/passwd", "x")
    (tmp_path / "tests").mkdir()
    with pytest.raises(ValueError): safe_write(tmp_path, "tests/test_a.py", "x", protected=["tests"])
    safe_write(tmp_path, "ok/new.py", "x", protected=["tests"])

def test_paid_provider_refused():
    with pytest.raises(ValueError): make_agent("coarena", "gpt-6-1-sol", "k")

def test_agent_with_fake_client_applies_files(tmp_path):
    class Msg: content = "FILE: s.py\n```python\nVALUE = 1\n```"
    class Ch: message = Msg()
    class Resp: choices = [Ch()]
    class Comp:
        def create(self, **k): return Resp()
    class Cl: chat = type("C", (), {"completions": Comp()})()
    make_agent("apinex", "free/x", "k", client=Cl())("goal", "", str(tmp_path))
    assert (tmp_path / "s.py").read_text() == "VALUE = 1\n"

def test_agent_records_token_usage_event(tmp_path):
    class Msg: content = "FILE: s.py\n```python\nVALUE = 1\n```"
    class Ch: message = Msg()
    class Usage: prompt_tokens = 11; completion_tokens = 7
    class Resp: choices = [Ch()]; usage = Usage()
    class Comp:
        def create(self, **k): return Resp()
    class Cl: chat = type("C", (), {"completions": Comp()})()
    make_agent("apinex", "free/x", "k", client=Cl())("goal", "", str(tmp_path))
    rows = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    call = [r for r in rows if r["kind"] == "llm_call"]
    assert call and call[0]["prompt_tokens"] == 11 and call[0]["completion_tokens"] == 7
    assert call[0]["provider"] == "apinex" and call[0]["model"] == "free/x"


def test_no_progress_guard_emits_advisory_warning(tmp_path):
    # dsh repeat-tool-reminder pattern: same failures + no file changes = looping, not working
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 3,
            "checks": [{"id": "C1", "cmd": "false"}]}
    status, _ = run_loop(spec, lambda g, f, w: None)
    assert status == "STOPPED_MAX_ITERS"
    warns = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()
             if '"kind": "warn"' in l]
    assert any("no progress" in w.get("what", "") for w in warns)


def test_per_check_timeout_from_spec(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 1, "check_timeout": 1,
            "checks": [{"id": "C1", "cmd": "sleep 5"}]}
    status, log = run_loop(spec, lambda g, f, w: None)
    assert status == "STOPPED_MAX_ITERS"
    assert log[0]["failed"] == ["C1"]


def test_big_check_output_spills_to_a_file(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 1,
            "checks": [{"id": "C1", "cmd": "python3 -c \"print('x' * 9000)\"; false"}]}
    status, log = run_loop(spec, lambda g, f, w: None)
    spilled = list((tmp_path / ".spill").glob("*.log"))
    assert spilled and len(spilled[0].read_text()) == 9001


def test_resume_continues_an_interrupted_run(tmp_path):
    """B6: a run stopped at max iters resumes from PROGRESS.json instead of starting over."""
    from rashi.loop import run_loop
    import json as _json
    spec = {"goal": "g", "checks": [{"id": "c1", "cmd": "test -f done.txt"}],
            "workdir": str(tmp_path), "max_iters": 3}
    calls = {"n": 0}
    def lazy(g, f, wd):  # never writes the file
        calls["n"] += 1
    status, log = run_loop(spec, lazy)
    assert status == "STOPPED_MAX_ITERS" and len(log) == 3 and calls["n"] == 3
    def finisher(g, f, wd):
        from pathlib import Path as P
        P(wd, "done.txt").write_text("x")
    spec2 = dict(spec, max_iters=5)
    status2, log2 = run_loop(spec2, finisher)
    assert status2 == "DONE_VERIFIED" and len(log2) == 4  # 3 old + 1 new, not 1 fresh
    events = [_json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(e.get("kind") == "resumed" and e.get("iters_done") == 3 for e in events)


def test_resume_ignores_other_goals_and_done_runs(tmp_path):
    from rashi.loop import run_loop
    spec = {"goal": "g", "checks": [{"id": "c1", "cmd": "true"}], "workdir": str(tmp_path)}
    assert run_loop(spec, lambda g, f, wd: None)[0] == "DONE_VERIFIED"
    # a DONE run never resumes; a different goal starts fresh
    assert run_loop(dict(spec, goal="other"), lambda g, f, wd: None)[0] == "DONE_VERIFIED"
    import json as _json
    assert not any(_json.loads(l).get("kind") == "resumed"
                   for l in (tmp_path / "events.jsonl").read_text().splitlines())


def test_regression_rolls_back_the_bad_step(tmp_path):
    """B5: an agent step that breaks a previously-passing check is undone and logged."""
    from rashi.loop import run_loop
    import json as _json
    (tmp_path / "a.txt").write_text("good")
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 4,
            "checks": [{"id": "a", "cmd": "grep -q good a.txt"},
                       {"id": "b", "cmd": "test -f b.txt"}, {"id": "c", "cmd": "test -f c.txt"}]}
    state = {"n": 0}
    def agent(g, f, wd):
        from pathlib import Path as P
        state["n"] += 1
        if state["n"] == 1:
            P(wd, "b.txt").write_text("x")           # iter 1: fixes b, c still failing
        elif state["n"] == 2:
            P(wd, "c.txt").write_text("x")           # iter 2: fixes c but...
            P(wd, "a.txt").write_text("broken")      #          REGRESSES a
        elif state["n"] == 3:
            P(wd, "c.txt").write_text("x")           # iter 3: re-fix c without touching a
    status, log = run_loop(spec, agent)
    assert status == "DONE_VERIFIED"
    assert (tmp_path / "a.txt").read_text() == "good"  # rolled back, not left broken
    events = [_json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    rb = [e for e in events if e.get("kind") == "rollback"]
    assert rb and rb[0]["restored"] == ["a.txt"] and rb[0]["deleted"] == ["c.txt"]


def test_rollback_deletes_added_files(tmp_path):
    from rashi.loop import run_loop
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 2,
            "checks": [{"id": "a", "cmd": "test -f keep.txt"}, {"id": "b", "cmd": "test ! -f junk.txt"}]}
    (tmp_path / "keep.txt").write_text("x")
    state = {"n": 0}
    def agent(g, f, wd):
        from pathlib import Path as P
        state["n"] += 1
        if state["n"] == 1:
            P(wd, "junk.txt").write_text("bad")      # breaks b (b was passing)
    run_loop(spec, agent)
    assert not (tmp_path / "junk.txt").exists()
