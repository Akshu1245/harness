"""Tests for fleet detection, CLI orchestration, and the standing rules wiring."""
import json
import pathlib
import stat
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from rashi import fleet, orchestrate, roles


# fleet: detection and readiness with fake CLIs on PATH
def _fake_cli(dirpath, name, body):
    p = dirpath / name
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_detect_ready_broken_absent(tmp_path, monkeypatch):
    _fake_cli(tmp_path, "codex", "#!/bin/sh\necho 'codex 1.2.3'\n")
    _fake_cli(tmp_path, "claude", "#!/bin/sh\nexit 1\n")
    monkeypatch.setenv("PATH", str(tmp_path))
    r = fleet.detect_all()
    assert r["codex"]["ready"] and "1.2.3" in r["codex"]["version"]
    assert r["claude"]["installed"] and not r["claude"]["ready"] and "fix" in r["claude"]
    assert not r["aider"]["installed"] and "pip install" in r["aider"]["fix"]
    text = fleet.report(r)
    assert text.splitlines()[0].startswith("READY")  # ready first


def test_probe_timeout_is_broken_not_crash(tmp_path, monkeypatch):
    _fake_cli(tmp_path, "gemini", "#!/bin/sh\nsleep 5\n")
    monkeypatch.setenv("PATH", str(tmp_path))
    r = fleet.probe("gemini", timeout=1)
    assert r["installed"] and not r["ready"]


# orchestrate: tasks close by exit codes, each in its own subdir
def _writer_cli(tmp_path, name, fail=False):
    if fail:
        return _fake_cli(tmp_path, name, "#!/bin/sh\nexit 1\n")
    return _fake_cli(tmp_path, name, '#!/bin/sh\necho x > "$PWD/out.txt"\n')


def test_run_tasks_distributes_and_verifies(tmp_path):
    good = _writer_cli(tmp_path, "goodcli")
    tasks = [{"id": "t1", "goal": "make out", "checks": [{"id": "C1", "cmd": "test -f out.txt"}]},
             {"id": "t2", "goal": "make out", "checks": [{"id": "C1", "cmd": "test -f out.txt"}]}]
    agents = {"good": [str(good)]}
    res = orchestrate.run_tasks(tasks, agents, tmp_path / "run")
    assert res == {"t1": "DONE_VERIFIED", "t2": "DONE_VERIFIED"}
    assert (tmp_path / "run" / "t1" / "out.txt").exists()  # own subdir per task


def test_failing_cli_never_done(tmp_path):
    bad = _writer_cli(tmp_path, "badcli", fail=True)
    tasks = [{"id": "t1", "goal": "g", "checks": [{"id": "C1", "cmd": "test -f out.txt"}]}]
    res = orchestrate.run_tasks(tasks, {"bad": [str(bad)]}, tmp_path / "run", max_iters=2)
    assert res["t1"] == "STOPPED_MAX_ITERS"


def test_no_ready_agent_assigns_nothing(tmp_path):
    tasks = [{"id": "t1", "goal": "g", "checks": [{"id": "C1", "cmd": "true"}]}]
    assert orchestrate.run_tasks(tasks, {}, tmp_path / "run")["t1"] == "NO_AGENT_AVAILABLE"
    assert orchestrate.assign(tasks, {}) == {}


def test_cli_agent_template_and_nonzero_raise():
    a = orchestrate.CliAgent.for_cli("codex")
    assert a.argv[:2] == ["codex", "exec"]
    with pytest.raises(ValueError):
        orchestrate.CliAgent.for_cli("not-a-cli")
    boom = orchestrate.CliAgent(["sh", "-c", "exit 3"])
    with pytest.raises(RuntimeError):
        boom("g", "", str(pathlib.Path.cwd()))


# rules: ponytail and no-ai-slop are wired into the roles that write code and prose
def test_roles_consult_standing_rules():
    assert "Smallest complete change" in roles.ROLES["coder"]["system"]
    assert "Smallest complete change" in roles.ROLES["planner"]["system"]
    assert "No AI slop" in roles.ROLES["reviewer"]["system"]
    assert "delve" in roles.ROLES["reviewer"]["system"]
