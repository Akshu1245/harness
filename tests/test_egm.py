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
