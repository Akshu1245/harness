"""Approval modes (his 2026-11-13 voice note): exactly three, no more.
full-access: complete access to the project, nothing is asked (a user-chosen setting for
his own project). review-and-accept: the spec and findings are shown, one accept/reject.
ask-for-everything: every finding and the spec each need an explicit yes.

The channel is separate from the mode: the terminal approver asks on stdin; the war-room
approver (file_approver) asks through the war-room page. Same three modes either way."""
import json
import time
from pathlib import Path

MODES = ("full-access", "review-and-accept", "ask-for-everything")


def approver(mode, input_fn=input, print_fn=print):
    """The approve(spec, findings) callback for one of exactly MODES."""
    if mode not in MODES:
        raise ValueError(f"unknown approval mode {mode!r}: exactly these exist: {', '.join(MODES)}")
    if mode == "full-access":
        return lambda spec, findings: True

    def show(spec, findings):
        print_fn(spec)
        if findings:
            print_fn("Findings:")
            for f in findings:
                print_fn(f"- [{f.get('severity', '?')}] {f.get('issue', '?')}")

    if mode == "review-and-accept":
        def review(spec, findings):
            show(spec, findings)
            return input_fn("Approve this spec? [y/N] ").strip().lower() == "y"
        return review

    def ask(spec, findings):
        show(spec, findings)
        for f in findings:
            if input_fn(f"Accept finding: {f.get('issue', '?')}? [y/N] ").strip().lower() != "y":
                return False
        return input_fn("Approve this spec? [y/N] ").strip().lower() == "y"
    return ask


def file_approver(mode, run_dir, poll_s=1.0, timeout_s=None):
    """Approval through the war-room page: writes PENDING_APPROVAL.json into the run dir and
    waits for the page's decision in APPROVAL_DECISION.json. Same three modes; full-access
    never writes anything. No decision before timeout is a NO - approval fails closed."""
    if mode not in MODES:
        raise ValueError(f"unknown approval mode {mode!r}: exactly these exist: {', '.join(MODES)}")
    if mode == "full-access":
        return lambda spec, findings: True
    run_dir = Path(run_dir)

    def decide(spec, findings):
        run_dir.mkdir(parents=True, exist_ok=True)
        pending = run_dir / "PENDING_APPROVAL.json"
        decision = run_dir / "APPROVAL_DECISION.json"
        pending.write_text(json.dumps({"mode": mode, "spec": spec, "findings": findings,
                                       "ts": time.time()}))
        start = time.time()
        try:
            while True:
                if decision.exists():
                    return bool(json.loads(decision.read_text()).get("approve"))
                if timeout_s is not None and time.time() - start > timeout_s:
                    return False
                time.sleep(poll_s)
        finally:
            pending.unlink(missing_ok=True)
            decision.unlink(missing_ok=True)
    return decide
