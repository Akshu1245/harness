import pytest
from rashi.llm_agent import make_agent


def test_kenari_paid_model_refused():
    with pytest.raises(ValueError):
        make_agent("kenari", "step-3-7-flash", "k", client=object())


def test_kenari_free_models_allowed():
    make_agent("kenari", "glm-4-7-flash:free", "k", client=object())
    make_agent("kenari", "kenari-free", "k", client=object())
