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
