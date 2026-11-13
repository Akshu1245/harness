import pytest
from rashi.llm_agent import SpendGate, make_agent


def test_kenari_paid_model_refused():
    with pytest.raises(ValueError):
        make_agent("kenari", "step-3-7-flash", "k", client=object())


def test_kenari_free_models_allowed():
    make_agent("kenari", "glm-4-7-flash:free", "k", client=object())
    make_agent("kenari", "kenari-free", "k", client=object())


def test_spend_gate_daily_cap(tmp_path):
    g = SpendGate(tmp_path / ".spend.json", per_day=2)
    g.check("kenari")
    g.check("kenari")
    with pytest.raises(RuntimeError):
        g.check("kenari")
    g.check("explabs")  # caps are per provider


def test_make_agent_refuses_paid_by_default_and_allows_explicit_optin():
    import pytest
    from rashi.llm_agent import make_agent
    with pytest.raises(ValueError, match="paid model refused"):
        make_agent("kenari", "glm-4.6", "k", client=object())
    a = make_agent("kenari", "glm-4.6", "k", client=object(), allow_paid=True)
    assert callable(a)


def test_every_role_prompt_carries_the_never_lie_rule():
    from rashi import roles
    assert all("exited 0" in r["system"] for r in roles.ROLES.values())


def test_openrouter_paid_model_also_needs_optin():
    import pytest
    from rashi.llm_agent import make_agent
    with pytest.raises(ValueError, match="paid model refused"):
        make_agent("openrouter", "openai/gpt-5", "k", client=object())
    assert callable(make_agent("openrouter", "some/model:free", "k", client=object()))


def test_rate_limit_retries_with_backoff_then_succeeds(tmp_path, monkeypatch):
    import time as time_mod
    from rashi.llm_agent import make_agent

    class FakeRateLimitError(Exception):
        status_code = 429

    calls = {"n": 0}

    class Msg:
        content = 'FILE: a.py\n```python\nx = 1\n```\n'

    class Completions:
        def create(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise FakeRateLimitError("429")
            return type("R", (), {"choices": [type("C", (), {"message": Msg()})()], "usage": None})()

    client = type("C", (), {"chat": type("X", (), {"completions": Completions()})()})()
    monkeypatch.setattr(time_mod, "sleep", lambda s: None)
    agent = make_agent("kenari", "kenari-free", "k", client=client)
    agent("goal", "", str(tmp_path))
    assert calls["n"] == 3 and (tmp_path / "a.py").read_text() == "x = 1\n"


def test_read_before_edit_refuses_to_clobber_a_changed_file(tmp_path):
    from rashi.llm_agent import make_agent
    (tmp_path / "a.py").write_text("original = 1\n")

    class Msg:
        content = 'FILE: a.py\n```python\nx = 2\n```\n'

    class Completions:
        def create(self, **kw):
            # a check or another process changes the file after the model read it
            (tmp_path / "a.py").write_text("someone_else = 3\n")
            return type("R", (), {"choices": [type("C", (), {"message": Msg()})()], "usage": None})()

    client = type("C", (), {"chat": type("X", (), {"completions": Completions()})()})()
    agent = make_agent("kenari", "kenari-free", "k", client=client)
    try:
        agent("goal", "", str(tmp_path))
        assert False, "should have refused"
    except ValueError as e:
        assert "changed since the model read it" in str(e)
    assert (tmp_path / "a.py").read_text() == "someone_else = 3\n"


def test_record_and_replay_a_run(tmp_path, monkeypatch):
    monkeypatch.setenv("RASHI_RECORD", "1")
    from rashi.llm_agent import make_agent
    from rashi.replay import replay_agent
    from rashi.loop import run_loop

    class Msg:
        content = 'FILE: a.py\n```python\nx = 1\n```\n'

    class Completions:
        def create(self, **kw):
            return type("R", (), {"choices": [type("C", (), {"message": Msg()})()], "usage": None})()

    client = type("C", (), {"chat": type("X", (), {"completions": Completions()})()})()
    live = tmp_path / "live"
    live.mkdir()
    agent = make_agent("kenari", "kenari-free", "k", client=client)
    agent("goal", "", str(live))
    assert (live / ".replay.jsonl").exists()
    # replay keylessly into a fresh workdir
    rep = tmp_path / "rep"
    rep.mkdir()
    replay_agent(live / ".replay.jsonl")("goal", "", str(rep))
    assert (rep / "a.py").read_text() == "x = 1\n"
