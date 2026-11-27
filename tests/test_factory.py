"""Factory mode: code-defined closed loop with local git versioning and agent review.
All offline: fake agents and fake reviewers, temp dirs only."""
import json
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


def test_definition_hash_stable(tmp_path):
    defn = factory.load(make_defn(tmp_path), tmp_path / "w")
    assert factory.definition_hash(defn) == factory.definition_hash(dict(defn))
    other = dict(defn, goal="different")
    assert factory.definition_hash(other) != factory.definition_hash(defn)
