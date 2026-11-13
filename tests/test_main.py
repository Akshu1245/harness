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
