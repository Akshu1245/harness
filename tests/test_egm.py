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
