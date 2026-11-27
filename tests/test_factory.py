"""Factory mode: code-defined closed loop with local git versioning and agent review.
All offline: fake agents and fake reviewers, temp dirs only."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from rashi import factory
from rashi.factory import FactoryError


def make_defn(tmp_path, **overrides):
    defn = {"goal": "write out.txt containing hello",
            "checks": [{"id": "out", "cmd": "grep -q hello out.txt"}],
            "git": "init", "max_iters": 3}
    defn.update(overrides)
    path = tmp_path / "factory.json"
    path.write_text(json.dumps(defn))
    return path


def agent_writes(text):
    def agent(goal, feedback, workdir):
        (Path(workdir) / "out.txt").write_text(text)
    return agent


def silent_agent(goal, feedback, workdir):
    pass


def git(workdir, *args):
    return subprocess.run(["git", *args], cwd=workdir, capture_output=True, text=True)


def test_done_verified_and_versioned(tmp_path):
    wd = tmp_path / "w"
    wd.mkdir()
    (wd / "seed.txt").write_text("starting state")
    result = factory.run_factory(make_defn(tmp_path), wd, agent_writes("hello"))
    assert result["status"] == "DONE_VERIFIED"
    assert result["iterations"] == 1
    log = git(wd, "log", "--format=%s").stdout.splitlines()
    assert any("iter 1" in m for m in log)
    assert any("baseline" in m for m in log)  # the starting tree is committed before the loop
    tracked = git(wd, "ls-files").stdout.splitlines()
    assert "seed.txt" in tracked
    assert "out.txt" in tracked
    assert "events.jsonl" not in tracked and "PROGRESS.json" not in tracked


def test_honest_failure_at_bound(tmp_path):
    result = factory.run_factory(make_defn(tmp_path), tmp_path / "w", silent_agent)
    assert result["status"] == "STOPPED_MAX_ITERS"
    assert result["iterations"] == 3
    assert result["status"] != "DONE_VERIFIED"


def test_git_required_fails_closed(tmp_path):
    calls = []
    def agent(goal, feedback, workdir):
        calls.append(1)
    path = make_defn(tmp_path, git=True)
    result = factory.run_factory(path, tmp_path / "w", agent)
    assert result["status"] == "FAILED_GIT_REQUIRED"
    assert calls == []


def test_git_false_runs_unversioned(tmp_path):
    result = factory.run_factory(make_defn(tmp_path, git=False), tmp_path / "w",
                                 agent_writes("hello"))
    assert result["status"] == "DONE_VERIFIED"
    assert result["git"] is False
    assert not (tmp_path / "w" / ".git").exists()


def test_review_rejection_is_feedback_then_done(tmp_path):
    seen = []
    replies = iter([(False, "diff lacks a trailing newline note"), (True, "ok")])
    def review(goal, feedback):
        seen.append(feedback)
        return next(replies)
    captured = []
    def agent(goal, feedback, workdir):
        captured.append(feedback)
        (Path(workdir) / "out.txt").write_text("hello")
    path = make_defn(tmp_path, review=True)
    result = factory.run_factory(path, tmp_path / "w", agent, review=review)
    assert result["status"] == "DONE_VERIFIED"
    assert result["iterations"] == 2
    assert "REJECTED" in captured[1] and "trailing newline" in captured[1]


def test_review_always_rejects_is_failed_review(tmp_path):
    path = make_defn(tmp_path, review=True, max_iters=2)
    result = factory.run_factory(path, tmp_path / "w", agent_writes("hello"),
                                 review=lambda goal, feedback: (False, "not good enough"))
    assert result["status"] == "FAILED_REVIEW"
    assert result["last"]["review"] == "rejected"


def test_review_true_needs_a_reviewer(tmp_path):
    result = factory.run_factory(make_defn(tmp_path, review=True), tmp_path / "w",
                                 agent_writes("hello"))
    assert result["status"] == "FAILED_REVIEWER_REQUIRED"


def test_protected_fixture_tamper_fails(tmp_path):
    wd = tmp_path / "w"
    wd.mkdir()
    (wd / "fixture.txt").write_text("do not touch")
    defn = {"goal": "g", "checks": [{"id": "out", "cmd": "grep -q hello out.txt"}],
            "protected": ["fixture.txt"], "git": "init", "max_iters": 2}
    path = tmp_path / "factory.json"
    path.write_text(json.dumps(defn))
    def bad_agent(goal, feedback, workdir):
        (Path(workdir) / "fixture.txt").write_text("touched")
        (Path(workdir) / "out.txt").write_text("hello")
    result = factory.run_factory(path, wd, bad_agent)
    assert result["status"] == "FAILED_TAMPERED_PROTECTED_FILES"


def test_definition_validation(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"goal": "g"}))
    with pytest.raises(FactoryError):
        factory.load(path, tmp_path)
    path.write_text(json.dumps({"goal": "g", "checks": [{"id": "x", "cmd": "true"}],
                                "protected": ["../escape"]}))
    with pytest.raises(FactoryError):
        factory.load(path, tmp_path)
    path.write_text(json.dumps({"goal": "g", "checks": [{"id": "x", "cmd": "true"}],
                                "review": "yes"}))
    with pytest.raises(FactoryError):
        factory.load(path, tmp_path)


def test_cli_reviewer_parsing(tmp_path):
    wd = tmp_path / "w"
    wd.mkdir()
    git(wd, "init")
    (wd / "f.txt").write_text("x")
    git(wd, "add", ".")
    git(wd, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "base")
    accept = factory.make_cli_reviewer(["sh", "-c", "cat >/dev/null; echo ACCEPT"], wd)
    assert accept("goal", "") == (True, "accepted")
    reject = factory.make_cli_reviewer(["sh", "-c", "cat >/dev/null; echo 'REJECT: wrong file'"], wd)
    ok, notes = reject("goal", "")
    assert ok is False and "wrong file" in notes
    garbage = factory.make_cli_reviewer(["sh", "-c", "cat >/dev/null; echo maybe"], wd)
    ok, notes = garbage("goal", "")
    assert ok is False and "unparseable" in notes
    missing = factory.make_cli_reviewer(["/nonexistent-reviewer-binary"], wd)
    ok, notes = missing("goal", "")
    assert ok is False and "unavailable" in notes


def test_cli_validate_only_needs_no_key(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("KENARI_API_KEY", raising=False)
    from rashi.__main__ import main
    rc = main(["factory", str(make_defn(tmp_path)), str(tmp_path / "w")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sha256" in out and "definition valid" in out


def fake_codex(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codex"
    fake.write_text("#!/bin/sh\necho hello > out.txt\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))


def test_cli_end_to_end_with_agent_and_reviewer(tmp_path, monkeypatch, capsys):
    fake_codex(tmp_path, monkeypatch)
    from rashi.__main__ import main
    path = make_defn(tmp_path, review=True)
    rc = main(["factory", str(path), str(tmp_path / "w"), "--agent", "codex",
               "--reviewer", "cat >/dev/null; echo ACCEPT", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0
    assert '"status": "DONE_VERIFIED"' in out


def test_cli_review_rejection_exits_nonzero(tmp_path, monkeypatch, capsys):
    fake_codex(tmp_path, monkeypatch)
    from rashi.__main__ import main
    path = make_defn(tmp_path, review=True, max_iters=2)
    rc = main(["factory", str(path), str(tmp_path / "w"), "--agent", "codex",
               "--reviewer", "cat >/dev/null; echo 'REJECT: no tests added'", "--yes"])
    out = capsys.readouterr().out
    assert rc == 1
    assert '"status": "FAILED_REVIEW"' in out


def test_cli_rejects_bad_definition(tmp_path, capsys):
    from rashi.__main__ import main
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"goal": "g"}))
    rc = main(["factory", str(bad), str(tmp_path / "w")])
    assert rc == 2
    assert "rejected" in capsys.readouterr().out


def test_artifacts_gate_missing_deliverable(tmp_path):
    path = make_defn(tmp_path, artifacts=["index.html", "report.md"])
    def agent(goal, feedback, workdir):
        (Path(workdir) / "out.txt").write_text("hello")
        (Path(workdir) / "index.html").write_text("hello")
    result = factory.run_factory(path, tmp_path / "w", agent)
    assert result["status"] == "FAILED_ARTIFACT_MISSING"
    assert result["missing_artifacts"] == ["report.md"]


def test_artifacts_gate_passes_and_lists(tmp_path):
    path = make_defn(tmp_path, artifacts=["out.txt"])
    result = factory.run_factory(path, tmp_path / "w", agent_writes("hello"))
    assert result["status"] == "DONE_VERIFIED"
    assert result["artifacts"] == ["out.txt"]


def test_artifact_path_validation(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"goal": "g", "checks": [{"id": "x", "cmd": "true"}],
                                "artifacts": ["../escape"]}))
    with pytest.raises(FactoryError):
        factory.load(path, tmp_path)


def test_artifact_symlink_counts_missing(tmp_path):
    wd = tmp_path / "w"
    wd.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("hello")
    defn = {"goal": "g", "checks": [{"id": "out", "cmd": "grep -q hello out.txt"}],
            "git": "init", "artifacts": ["out.txt"], "max_iters": 2}
    path = tmp_path / "factory.json"
    path.write_text(json.dumps(defn))
    def agent(goal, feedback, workdir):
        (Path(workdir) / "out.txt").symlink_to(outside)  # a link is not a produced artifact
    result = factory.run_factory(path, wd, agent)
    assert result["status"] == "FAILED_ARTIFACT_MISSING"


def test_preview_serves_the_artifact(tmp_path):
    wd = tmp_path / "w"
    wd.mkdir()
    (wd / "index.html").write_text("<h1>real artifact</h1>")
    server = factory.serve_preview(wd, port=0)
    import threading, urllib.request
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        body = urllib.request.urlopen(url, timeout=5).read().decode()
        assert "real artifact" in body
    finally:
        server.shutdown()
        server.server_close()


def test_preview_kind_detects_streamlit_app(tmp_path):
    assert factory.preview_kind(tmp_path) == "static"
    (tmp_path / "app.py").write_text("import streamlit as st")
    assert factory.preview_kind(tmp_path) == "streamlit"


def test_streamlit_preview_missing_entry(tmp_path):
    with pytest.raises(FactoryError):
        factory.streamlit_preview(tmp_path, port=9999)


def test_streamlit_preview_serves_a_real_app(tmp_path):
    pytest.importorskip("streamlit")
    import socket, time, urllib.request
    (tmp_path / "app.py").write_text(
        "import streamlit as st\nst.title('factory real app')\n")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = factory.streamlit_preview(tmp_path, port=port)
    try:
        body = None
        for _ in range(60):
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read()
                break
            except OSError:
                time.sleep(0.5)
        assert body is not None and b"streamlit" in body.lower()
    finally:
        proc.terminate()
        proc.wait(timeout=15)


def test_definition_hash_stable(tmp_path):
    defn = factory.load(make_defn(tmp_path), tmp_path / "w")
    assert factory.definition_hash(defn) == factory.definition_hash(dict(defn))
    other = dict(defn, goal="different")
    assert factory.definition_hash(other) != factory.definition_hash(defn)
