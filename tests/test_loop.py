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
