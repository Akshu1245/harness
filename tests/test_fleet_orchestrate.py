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


def test_plain_callable_agent_accepted(tmp_path):
    def agent(goal, feedback, wd):
        pathlib.Path(wd, "out.txt").write_text("x")
    tasks = [{"id": "t1", "goal": "g", "checks": [{"id": "C1", "cmd": "test -f out.txt"}]}]
    assert orchestrate.run_tasks(tasks, {"fn": agent}, tmp_path / "run")["t1"] == "DONE_VERIFIED"


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


def test_run_tasks_passes_sibling_changes_to_later_tasks(tmp_path):
    """ACM EXPRESS'26 (pass 3, pain 10): telling the next task what earlier siblings
    changed recovers most pass-alone/fail-together runs. The second task's goal must
    name the files the first one touched; the first task's goal stays clean."""
    import pathlib
    seen_goals = []

    def agent(goal, fb, wd):
        seen_goals.append(goal)
        (pathlib.Path(wd) / "helpers.py").write_text("def shout(s):\n    return s.upper()\n")

    tasks = [{"id": "t1", "goal": "make helpers", "checks": [{"id": "C1", "cmd": "true"}]},
             {"id": "t2", "goal": "use helpers", "checks": [{"id": "C1", "cmd": "true"}]}]
    res = orchestrate.run_tasks(tasks, {"a": agent}, tmp_path / "run")
    assert res == {"t1": "DONE_VERIFIED", "t2": "DONE_VERIFIED"}
    assert "Sibling tasks" not in seen_goals[0]
    assert "t1: helpers.py" in seen_goals[1]


def test_hung_cli_agent_is_killed_and_recorded_not_done(tmp_path):
    """Pass 4 (Reddit pain 26): users report agents hanging 40-55 minutes on a silently
    stuck call. A hung CLI here is killed at its timeout, recorded as an agent error,
    and the run ends STOPPED - never DONE, never a zombie."""
    import time
    sleepy = _fake_cli(tmp_path, "sleepycli", "#!/bin/sh\nsleep 30\n")
    tasks = [{"id": "t1", "goal": "g", "checks": [{"id": "C1", "cmd": "test -f out.txt"}]}]
    t0 = time.time()
    res = orchestrate.run_tasks(tasks, {"slow": orchestrate.CliAgent([str(sleepy)], timeout=1)},
                                tmp_path / "run", max_iters=1)
    assert time.time() - t0 < 10  # the hang was cut, not waited out
    assert res["t1"] != "DONE_VERIFIED"
    progress = (tmp_path / "run" / "t1" / "PROGRESS.json").read_text()
    assert "TimeoutExpired" in progress or "STOPPED" in progress


def test_task_ids_cannot_escape_or_collide(tmp_path):
    import pytest
    from rashi.orchestrate import run_tasks
    calls=[]
    def agent(*a): calls.append(a)
    for tasks in ([{'id':'../../elsewhere','goal':'g','checks':[]}],
                  [{'id':'same','goal':'g','checks':[]},{'id':'same','goal':'g','checks':[]}]):
        with pytest.raises(ValueError):
            run_tasks(tasks,{'fake':agent},str(tmp_path))
    assert calls == []


def test_task_directory_symlink_is_refused(tmp_path):
    import pytest
    from rashi.orchestrate import run_tasks
    outside=tmp_path/'outside'; outside.mkdir()
    base=tmp_path/'base'; base.mkdir(); (base/'t1').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        run_tasks([{'id':'t1','goal':'g','checks':[]}],{'fake':lambda *a:None},str(base))
