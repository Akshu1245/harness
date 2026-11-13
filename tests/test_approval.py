import pytest

from rashi import approval


def test_exactly_three_modes_exist():
    # his 2026-11-13 voice note: full access, review and accept, ask for everything - no more
    assert approval.MODES == ("full-access", "review-and-accept", "ask-for-everything")


def test_full_access_never_asks():
    a = approval.approver("full-access", input_fn=lambda p: (_ for _ in ()).throw(AssertionError("asked")))
    assert a("spec", [{"issue": "x"}]) is True


def test_review_and_accept_asks_once():
    asked = []
    a = approval.approver("review-and-accept", input_fn=lambda p: asked.append(p) or "y", print_fn=lambda *a: None)
    assert a("spec", [{"issue": "x"}, {"issue": "y"}]) is True
    assert len(asked) == 1


def test_ask_for_everything_asks_per_finding_and_rejects_one_no():
    answers = iter(["y", "n", "y"])
    a = approval.approver("ask-for-everything", input_fn=lambda p: next(answers), print_fn=lambda *a: None)
    assert a("spec", [{"issue": "one"}, {"issue": "two"}]) is False  # the 'n' on finding two


def test_unknown_mode_refused():
    with pytest.raises(ValueError):
        approval.approver("yolo-mode")
