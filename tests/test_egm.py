import json
from rashi import egm


def test_goldfish_sees_only_spec_and_files(tmp_path):
    (tmp_path / "a.py").write_text("x=1")
    seen = []
    def llm(sys, user):
        seen.append(user); return '{"findings":[]}'
    egm.goldfish_review(llm, "Goal\n- `a.py`\n", str(tmp_path))
    assert "x=1" in seen[0] and "Project context" not in seen[0]


def test_unparsable_reviewer_is_high_finding(tmp_path):
    f = egm.goldfish_review(lambda s, u: "lol", "spec", str(tmp_path))
    assert f[0]["severity"] == "high"


def test_spec_gate_revises_then_extracts_checks(tmp_path):
    calls = []
    def llm(sys, user):
        calls.append(sys)
        if sys == egm.GOLDFISH_SYS:
            n = calls.count(egm.GOLDFISH_SYS)
            return json.dumps({"findings": [{"severity": "high" if n == 1 else "low", "issue": "no check", "evidence": ""}]})
        return "Goal\nChecks\n- `pytest -q`\n"
    spec, findings, checks = egm.spec_gate(llm, "g", str(tmp_path))
    assert checks == [{"id": "c1", "cmd": "pytest -q"}]
    assert calls.count(egm.ELEPHANT_SYS) == 2


def test_drift(tmp_path):
    (tmp_path / "ok.py").write_text("")
    r = egm.drift_report("`ok.py` `gone.py`", str(tmp_path))
    assert r["missing_paths"] == ["gone.py"]


def test_checks_on_missing_files_are_rejected(tmp_path):
    (tmp_path / "t.py").write_text("")
    bad = lambda s, u: '{"findings":[]}' if s == egm.GOLDFISH_SYS else "Checks\n- `python -m pytest t.py nope.py`\n"
    spec, findings, checks = egm.spec_gate(bad, "g", str(tmp_path))
    assert checks == [] and any("nope.py" in f["issue"] for f in findings)
    good = lambda s, u: '{"findings":[]}' if s == egm.GOLDFISH_SYS else "Checks\n- `python -m pytest t.py`\n"
    assert egm.spec_gate(good, "g", str(tmp_path))[2] != []


def test_revision_that_drops_checks_keeps_last_valid(tmp_path):
    (tmp_path / "t.py").write_text("")
    n = {"g": 0}
    def llm(s, u):
        if s == egm.GOLDFISH_SYS:
            n["g"] += 1
            return '{"findings":[{"severity":"high","issue":"x","evidence":""}]}'
        return "Checks\n- `python t.py`\n" if "Revise" not in u else "no checks here"
    spec, findings, checks = egm.spec_gate(llm, "g", str(tmp_path))
    assert checks == [{"id": "c1", "cmd": "python t.py"}]


def test_goldfish_retries_once_on_unparsable(tmp_path):
    calls = {"n": 0}
    def llm(s, u):
        calls["n"] += 1
        return "lol" if calls["n"] == 1 else '{"findings":[{"severity":"low","issue":"ok"}]}'
    f = egm.goldfish_review(llm, "spec", str(tmp_path))
    assert f == [{"severity": "low", "issue": "ok"}] and calls["n"] == 2


def test_draft_spec_retries_an_empty_reply():
    """Dogfood 2026-11-13: Kenari's flash model answered a spec prompt with an empty
    message; the draft must ask once more instead of flowing an empty spec downstream."""
    calls = []

    def llm(system, user):
        calls.append(user)
        return "" if len(calls) == 1 else "Spec\n- `test -f x.py`"

    from rashi.egm import draft_spec
    assert draft_spec(llm, "make x") == "Spec\n- `test -f x.py`"
    assert len(calls) == 2 and "previous reply was empty" in calls[1]


def test_brainstorm_brief_then_challenge_revision():
    """EGM brainstorm: elephant drafts a brief, fresh goldfish challenges it, elephant
    revises once when the challenge has a high finding."""
    calls = []
    def llm(system, user):
        calls.append(system)
        if system == egm.CHALLENGE_SYS:
            return '{"findings":[{"severity":"high","issue":"fuzzy goal","evidence":"no metric"}]}'
        return "Problem\nx\n" if "Revise" not in user else "Problem\nx revised\n"
    brief, findings = egm.brainstorm(llm, "idea")
    assert brief.endswith("revised\n") and findings[0]["issue"] == "fuzzy goal"
    assert calls == [egm.BRIEF_SYS, egm.CHALLENGE_SYS, egm.BRIEF_SYS]


def test_brainstorm_keeps_brief_when_challenge_is_low():
    def llm(system, user):
        return '{"findings":[{"severity":"low","issue":"nit","evidence":""}]}' if system == egm.CHALLENGE_SYS \
            else "Problem\nx\n"
    brief, _ = egm.brainstorm(llm, "idea")
    assert brief == "Problem\nx\n"


def test_brainstorm_retries_empty_reply():
    calls = []
    def llm(system, user):
        calls.append(user)
        if system == egm.CHALLENGE_SYS:
            return '{"findings":[]}'
        return "" if len(calls) == 1 else "Problem\nx\n"
    brief, _ = egm.brainstorm(llm, "idea")
    assert brief == "Problem\nx\n" and "previous reply was empty" in calls[1]
