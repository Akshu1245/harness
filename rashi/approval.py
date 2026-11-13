"""Approval modes (his 2026-11-13 voice note): exactly three, no more.
full-access: complete access to the project, nothing is asked (a user-chosen setting for
his own project). review-and-accept: the spec and findings are shown, one accept/reject.
ask-for-everything: every finding and the spec each need an explicit yes."""

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
