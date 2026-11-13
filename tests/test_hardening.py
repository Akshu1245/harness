"""Hardening tests (2026-11-13): failure paths the first suite did not cover."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from rashi import bounty, egm
from rashi.llm_agent import make_agent
from rashi.loop import run_loop
from rashi.netguard import url_is_public


def _fake(*ips):
    return lambda h, p: [(2, 1, 6, "", (ip, 0)) for ip in ips]


# netguard: ranges Python 3.10's flags miss, and multi-answer DNS
def test_ssrf_blocks_ula_cgnat_unspecified_and_mapped():
    for ip in ("fc00::1", "fd12::9", "100.64.0.1", "0.0.0.0", "::", "::ffff:127.0.0.1"):
        assert not url_is_public("http://x.example/", resolver=_fake(ip)), ip


def test_ssrf_blocks_when_any_answer_is_private():
    assert not url_is_public("http://x.example/", resolver=_fake("93.184.216.34", "10.1.2.3"))


def test_ssrf_still_allows_public():
    assert url_is_public("https://example.com/", resolver=_fake("93.184.216.34"))


# loop: a check command must not be able to modify protected files
def test_check_tampering_protected_file_fails(tmp_path):
    (tmp_path / "guard.txt").write_text("locked")
    spec = {"goal": "g", "workdir": str(tmp_path), "protected": ["guard.txt"], "max_iters": 3,
            "checks": [{"id": "C1", "cmd": "echo hacked > guard.txt"}]}
    st, log = run_loop(spec, lambda g, f, w: None)
    assert st == "FAILED_TAMPERED_PROTECTED_FILES"
    assert log[0].get("tampered_by") == "checks"


def test_absent_protected_path_is_logged_not_silent(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path), "protected": ["nope.txt"], "max_iters": 1,
            "checks": [{"id": "C1", "cmd": "true"}]}
    st, _ = run_loop(spec, lambda g, f, w: None)
    assert st == "DONE_VERIFIED"
    events = [json.loads(l) for l in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(e["kind"] == "warn" and e.get("paths") == ["nope.txt"] for e in events)


def test_missing_workdir_is_created_not_a_crash(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path / "new"), "max_iters": 1,
            "checks": [{"id": "C1", "cmd": "true"}]}
    st, _ = run_loop(spec, lambda g, f, w: None)
    assert st == "DONE_VERIFIED" and (tmp_path / "new" / "PROGRESS.json").exists()


def test_unspawnable_check_is_a_failed_check_not_a_crash(tmp_path):
    from rashi.loop import run_cmd
    code, out = run_cmd("true", str(tmp_path / "no-such-dir"))
    assert code == 2 and "spawn error" in out


# egm: drift path rule matches invalid_checks; version numbers are not paths
def test_drift_flags_slash_and_shell_js_but_not_versions(tmp_path):
    (tmp_path / "ok.py").write_text("")
    r = egm.drift_report("`ok.py` `gone.sh` `sub/gone.js` `3.11`", str(tmp_path))
    assert r["missing_paths"] == ["gone.sh", "sub/gone.js"] and r["drifted"]


# llm_agent: prompt context is bounded no matter how many files exist
def test_agent_context_is_capped(tmp_path):
    for i in range(30):
        (tmp_path / f"f{i:02d}.py").write_text("x = 1\n" + "#" * 2500)
    seen = {}

    class Msg:
        content = "FILE: s.py\n```python\nVALUE = 1\n```"

    class Ch:
        message = Msg()

    class Resp:
        choices = [Ch()]

    class Comp:
        def create(self, **k):
            seen["prompt"] = k["messages"][1]["content"]
            return Resp()

    class Cl:
        chat = type("C", (), {"completions": Comp()})()

    make_agent("apinex", "free/x", "k", client=Cl())("goal", "", str(tmp_path))
    assert len(seen["prompt"]) < 30000


# bounty: URL spelling tricks must not escape the scope rules
def test_scope_userinfo_port_case_and_trailing_dot():
    s = bounty.Scope({"program": "p", "policy_url": "https://x/p", "date": "2026-11-13",
                      "in_scope": ["*.ex.com"], "out_of_scope": []})
    assert s.allows("https://user:pass@api.ex.com:8443/x")[0]
    assert s.allows("https://API.EX.COM./")[0]
    assert not s.allows("https://ex.com/")[0]
    assert not s.allows("https://ex.com.evil.com/")[0]


# SpendGate: cap enforcement, day rollover, corrupt-state recovery
def test_spend_gate_cap_rollover_and_corrupt_file(tmp_path):
    from rashi.llm_agent import SpendGate
    g = SpendGate(tmp_path / ".spend.json", per_day=2)
    g.check("kenari"); g.check("kenari")
    with pytest.raises(RuntimeError):
        g.check("kenari")
    g.check("apinex")  # cap is per provider
    (tmp_path / ".spend.json").write_text("{corrupt")
    g.check("kenari")  # corrupt state recovers to a fresh day instead of crashing
    data = json.loads((tmp_path / ".spend.json").read_text())
    assert data["calls"] == {"kenari": 1}
