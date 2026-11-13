"""Front door: python -m rashi fleet|build|warroom."""
import pathlib
import stat
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rashi.__main__ import find_llm, main


def test_fleet_command_prints_report(tmp_path, monkeypatch, capsys):
    exe = tmp_path / "codex"
    exe.write_text("#!/bin/sh\necho codex-9\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert main(["fleet"]) == 0
    out = capsys.readouterr().out
    assert "READY" in out and "codex" in out and "ABSENT" in out


def test_find_llm_prefers_configured_free_provider():
    assert find_llm({}) is None
    assert find_llm({"KENARI_API_KEY": "k"}) == ("kenari", "glm-4-7-flash:free", "k")
    # respan has no verified free default model: not picked even with a key
    assert find_llm({"RESPAN_API_KEY": "k"}) is None


def test_build_without_key_exits_clean(capsys):
    import os
    for v in ("KENARI_API_KEY", "EXPLABS_API_KEY", "APINEX_API_KEY", "RESPAN_API_KEY", "OPENROUTER_API_KEY"):
        os.environ.pop(v, None)
    assert main(["build", "make x", "/tmp/x"]) == 2
    assert "No free provider key" in capsys.readouterr().err


def test_bench_command_wires_live_runner(tmp_path, monkeypatch, capsys):
    from rashi import __main__ as m
    monkeypatch.setattr(m, "find_llm", lambda: ("kenari", "glm-4-7-flash:free", "k"))
    made = {}
    monkeypatch.setattr(m, "make_agent", lambda p, mod, k: made.setdefault("agent", (p, mod, k)) or object())
    seen = {}

    def fake_loop(spec, agent):
        seen.setdefault("specs", []).append(spec)
        return "DONE_VERIFIED", []

    monkeypatch.setattr(m, "run_loop", fake_loop)
    out = tmp_path / "r.jsonl"
    rc = m.main(["bench", "--out", str(out), "--dir", str(tmp_path / "wd")])
    assert rc == 0
    assert made["agent"] == ("kenari", "glm-4-7-flash:free", "k")
    assert len(seen["specs"]) == 4  # one run_loop per benchmark task
    assert all(s["checks"][0]["id"].endswith("-c1") for s in seen["specs"])
    guard = next(s for s in seen["specs"] if s["checks"][0]["id"].startswith("bench-guard"))
    assert guard["protected"] == ["helpers.py", "test_helpers.py"]
    assert (tmp_path / "wd" / "bench-guard" / "helpers.py").exists()  # seeded before the loop
    rows = out.read_text().splitlines()
    assert len(rows) == 4 and all('"DONE_VERIFIED"' in r for r in rows)
    assert '"pass_rate": 1.0' in capsys.readouterr().out


def test_bench_seeded_guarded_task_runs_and_protects(tmp_path, monkeypatch):
    """End to end: a seeded task's files exist before the loop, the agent may
    add new files beside them, and touching a protected file fails the run."""
    import json as j
    from rashi import __main__ as m
    monkeypatch.setattr(m, "find_llm", lambda: ("kenari", "glm-4-7-flash:free", "k"))
    tasks = tmp_path / "tasks.json"
    tasks.write_text(j.dumps([{
        "id": "guard",
        "goal": "make greeter.py",
        "seed": {"helpers.py": "def shout(s):\n    return s.upper() + '!'\n"},
        "protected": ["helpers.py"],
        "checks": ["python -c \"from greeter import greet; assert greet('bo') == 'HELLO BO!'\""],
    }, {
        "id": "tamper",
        "goal": "make greeter.py",
        "seed": {"helpers.py": "def shout(s):\n    return s.upper() + '!'\n"},
        "protected": ["helpers.py"],
        "checks": ["true"],
    }]))

    def good(goal, fb, wd):
        (pathlib.Path(wd) / "greeter.py").write_text(
            "from helpers import shout\n\ndef greet(name):\n    return shout('hello ' + name)\n")

    def bad(goal, fb, wd):
        (pathlib.Path(wd) / "helpers.py").write_text("# hijacked\n")

    queue = {"guard": good, "tamper": bad}

    def fake_loop(spec, agent):
        from rashi.loop import run_loop as real_loop
        return real_loop(spec, queue[pathlib.Path(spec["workdir"]).name])

    monkeypatch.setattr(m, "run_loop", fake_loop)
    out = tmp_path / "r.jsonl"
    rc = m.main(["bench", "--tasks", str(tasks), "--out", str(out), "--dir", str(tmp_path / "wd")])
    assert rc == 1  # the tamper task must fail, so the bench cannot be all-green
    rows = [j.loads(r) for r in out.read_text().splitlines()]
    assert rows[0]["status"] == "DONE_VERIFIED"  # added a file, left the protected one alone
    assert rows[1]["status"] == "FAILED_TAMPERED_PROTECTED_FILES"  # rewrote the seeded file
    assert (tmp_path / "wd" / "guard" / "helpers.py").read_text() == "def shout(s):\n    return s.upper() + '!'\n"


def test_bench_without_key_exits_clean(capsys, monkeypatch):
    from rashi import __main__ as m
    monkeypatch.setattr(m, "find_llm", lambda: None)
    assert m.main(["bench"]) == 2
    assert "No free provider key" in capsys.readouterr().err
