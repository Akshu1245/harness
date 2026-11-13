import json

from rashi.memory import recall, remember
from rashi.loop import run_loop


def test_remember_recall_roundtrip(tmp_path):
    assert recall(str(tmp_path)) == ""
    remember(str(tmp_path), "note", "first")
    remember(str(tmp_path), "done", "second")
    out = recall(str(tmp_path))
    assert "[note] first" in out and out.endswith("[done] second")


def test_recall_caps_and_survives_corrupt_lines(tmp_path):
    store = tmp_path / ".rashi" / "memory.jsonl"
    store.parent.mkdir(parents=True)
    store.write_text('{"kind":"note","text":"old"}\nnot json\n{"kind":"note","text":"new"}\n')
    out = recall(str(tmp_path))
    assert "new" in out and "old" in out  # corrupt line skipped
    for i in range(100):
        remember(str(tmp_path), "note", f"r{i}")
    capped = recall(str(tmp_path), max_chars=100)
    assert len(capped) < 200 and "r99" in capped


def test_loop_records_done_and_rollback(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 2,
            "checks": [{"id": "a", "cmd": "test ! -f bad.txt"}]}
    state = {"n": 0}
    def agent(g, f, wd):
        from pathlib import Path as P
        state["n"] += 1
        if state["n"] == 1:
            P(wd, "bad.txt").write_text("x")  # regresses the initially-passing check
    assert run_loop(spec, agent)[0] == "DONE_VERIFIED"
    out = recall(str(tmp_path))
    assert "rollback" in out and "DONE_VERIFIED" in out


def test_pipeline_context_carries_memory(tmp_path):
    from rashi.pipeline import run_pipeline
    remember(str(tmp_path), "note", "checks need pytest")
    seen = []
    def llm(system, user):
        seen.append(user)
        return '{"findings":[]}' if "fresh reviewer" in system else "Checks\n- `true`\n"
    run_pipeline("g", str(tmp_path), llm, lambda g, f, wd: None, lambda s, f: True)
    assert any("checks need pytest" in u for u in seen)
