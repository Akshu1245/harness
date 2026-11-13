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
