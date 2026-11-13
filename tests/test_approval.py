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


def test_file_approver_full_access_writes_nothing(tmp_path):
    a = approval.file_approver("full-access", tmp_path)
    assert a("spec", []) is True
    assert not (tmp_path / "PENDING_APPROVAL.json").exists()


def test_file_approver_waits_for_the_pages_decision(tmp_path):
    import json, threading, time
    a = approval.file_approver("review-and-accept", tmp_path, poll_s=0.05)

    def answer():
        while not (tmp_path / "PENDING_APPROVAL.json").exists():
            time.sleep(0.02)
        assert "the spec" in (tmp_path / "PENDING_APPROVAL.json").read_text()
        (tmp_path / "APPROVAL_DECISION.json").write_text(json.dumps({"approve": True}))
    threading.Thread(target=answer).start()
    assert a("the spec", []) is True
    assert not (tmp_path / "PENDING_APPROVAL.json").exists()  # cleaned up after the decision


def test_file_approver_fails_closed_on_timeout(tmp_path):
    a = approval.file_approver("ask-for-everything", tmp_path, poll_s=0.02, timeout_s=0.1)
    assert a("spec", [{"issue": "x"}]) is False
