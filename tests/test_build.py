"""One-press build flow and the creation-check fix in the spec gate."""
import pathlib
import stat
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from rashi import build, egm


def _cli(dirpath, name, body):
    p = dirpath / name
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def llm_ok(system, user):
    if "fresh reviewer" in system:
        return '{"findings":[]}'
    if "Split this spec" in system:
        return '{"tasks":[{"id":"a","goal":"make out.txt","checks":["test -f out.txt"]}]}'
    return "Goal\nChecks\n- `test -f out.txt`\n"


def test_creation_check_on_missing_file_is_allowed(tmp_path):
    bad = egm.invalid_checks([{"id": "c1", "cmd": "test -f app.py"}], str(tmp_path))
    assert bad == []  # absence is what the check asserts
    still_bad = egm.invalid_checks([{"id": "c1", "cmd": "python app.py"}], str(tmp_path))
    assert still_bad and "missing file app.py" in still_bad[0]["issue"]


def test_split_fallback_when_planner_json_unparsable():
    tasks, how = build.split_tasks(lambda s, u: "no json", "spec", [{"id": "c1", "cmd": "true"}])
    assert how == "fallback_single_task" and tasks[0]["checks"] == [{"id": "t1-c1", "cmd": "true"}]


def test_one_press_end_to_end(tmp_path):
    agent = _cli(tmp_path, "mkcli", '#!/bin/sh\necho x > "$PWD/out.txt"\n')
    r = build.one_press("make out", str(tmp_path / "run"), llm_ok, lambda s, f: True,
                        agents={"mk": [agent]})
    assert r["status"] == "DONE_VERIFIED" and r["tasks"] == {"a": "DONE_VERIFIED"}
    assert r["split"] == "split"


def test_one_press_gates(tmp_path):
    agent = _cli(tmp_path, "mkcli", '#!/bin/sh\necho x > "$PWD/out.txt"\n')
    r = build.one_press("g", str(tmp_path / "n"), llm_ok, lambda s, f: False, agents={"mk": [agent]})
    assert r["status"] == "SPEC_NOT_APPROVED"
    r2 = build.one_press("g", str(tmp_path / "m"), llm_ok, lambda s, f: True, agents={},
                         fleet_results={"codex": {"ready": False, "installed": False,
                                                  "cmd": "codex", "name": "Codex", "fix": "install"}})
    assert r2["status"] == "NO_READY_AGENTS" and "codex" in r2["fleet"]


def test_ready_agents_filters_and_templates():
    fr = {"codex": {"ready": True}, "aider": {"ready": False}, "unknown": {"ready": True}}
    ra = build.ready_agents(fr)
    assert list(ra) == ["codex"] and ra["codex"][0] == "codex"


def test_split_retries_once_on_unparsable_then_succeeds():
    calls = {"n": 0}
    def llm(s, u):
        calls["n"] += 1
        return "prose" if calls["n"] == 1 else '{"tasks":[{"id":"a","goal":"g","checks":["true"]}]}'
    tasks, how = build.split_tasks(llm, "spec", [{"id": "c1", "cmd": "true"}])
    assert how == "split" and calls["n"] == 2 and tasks[0]["id"] == "a"
