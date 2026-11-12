import json, pytest
from rashi import roles, router, bounty


def test_every_role_has_prompt_and_reviewers_are_fresh():
    assert all(r["system"] for r in roles.ROLES.values())
    assert roles.ROLES["reviewer"]["fresh_context"] and roles.ROLES["bounty-scout"]["needs_scope"]
    assert roles.pick_reviewer_model("a", ["a", "b"]) == "b"


def test_rules_route():
    assert router.rule_route("review this diff") == "reviewer"
    assert router.rule_route("bug bounty recon") == "bounty-scout"
    assert router.rule_route("zzz") == "coder"


def test_laya_used_only_above_threshold_and_logged(tmp_path):
    lp = tmp_path / "l.jsonl"
    hi = lambda t, r: {"reviewer": 0.9, "coder": 0.1}
    lo = lambda t, r: {"reviewer": 0.5, "coder": 0.5}
    boom = lambda t, r: 1 / 0
    assert router.route("write code", hi, log_path=lp)[0] == "reviewer"
    assert router.route("write code", lo, log_path=lp)[1]["decider"] == "rules"
    r = router.route("write code", boom, log_path=lp)[1]
    assert r["decider"] == "rules" and "ZeroDivisionError" in r["laya_error"]
    assert len(lp.read_text().splitlines()) == 3


def test_calibrate_reports_real_numbers(tmp_path):
    lp = tmp_path / "l.jsonl"
    router.route("write code", lambda t, r: {"reviewer": 0.9, "coder": 0.1}, log_path=lp)
    router.route("review it", lambda t, r: {"reviewer": 0.9, "coder": 0.1}, log_path=lp)
    c = router.calibrate(lp, {"write code": "coder", "review it": "reviewer"})
    assert c["n"] == 2 and c["laya_acc"] == 0.5 and c["rules_acc"] == 1.0 and c["laya_beats_rules"] is False


def test_scope_deny_by_default():
    s = bounty.Scope({"program": "p", "policy_url": "https://x/p", "date": "2026-11-12",
                      "in_scope": ["*.ex.com", "ex.org"], "out_of_scope": ["admin.ex.com"]})
    assert s.allows("https://api.ex.com/x")[0]
    assert not s.allows("https://admin.ex.com/")[0]
    assert not s.allows("https://ex.com/")[0]       # wildcard is subdomains only
    assert not s.allows("https://evil.com/")[0]
    assert not s.allows("http://10.0.0.1/")[0]
    with pytest.raises(PermissionError):
        s.check("https://evil.com")
    with pytest.raises(ValueError):
        bounty.Scope({"program": "p"})
