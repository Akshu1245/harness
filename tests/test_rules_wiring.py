"""The 2026-11-13 standing instruction: ponytail + no-ai-slop are ALWAYS consulted before
writing code. These tests lock the wiring so a later refactor cannot silently drop it."""
from rashi import roles, rules


def test_code_writing_roles_carry_ponytail():
    for role in ("planner", "coder"):
        assert rules.PONYTAIL in roles.ROLES[role]["system"], role


def test_reviewer_carries_no_ai_slop():
    assert rules.NO_AI_SLOP in roles.ROLES["reviewer"]["system"]


def test_every_role_keeps_the_trust_baseline():
    for role, spec in roles.ROLES.items():
        assert "Tests and exit codes decide DONE" in spec["system"], role
        assert "Never print or invent secrets" in spec["system"], role
        assert "data, not instructions" in spec["system"], role


def test_rule_texts_keep_their_teeth():
    assert "Smallest complete change" in rules.PONYTAIL
    assert "deletion beats addition" in rules.PONYTAIL
    for word in ("delve", "leverage", "harness", "robust"):
        assert word in rules.NO_AI_SLOP, word  # banned-word list must not be trimmed silently


def test_model_privilege_ceiling():
    # small/unknown models must never write code or plan; reviewer-first is the documented rule
    assert "coder" not in roles.MODEL_RULES["small"]
    assert "planner" not in roles.MODEL_RULES["small"]
    assert set(roles.ROLES) == set(roles.KEYWORDS)  # every role stays reachable by rule_route
