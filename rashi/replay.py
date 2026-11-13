"""Keyless replay of a recorded agent run (pattern from dsh test-support/llm-replay).
record: RASHI_RECORD=1 during a live run writes .replay.jsonl in the workdir.
replay: replay_agent(path) is a loop-compatible agent that re-applies the recorded
file writes, one recorded response per call, and says so when the tape runs out."""
import json
from pathlib import Path

from .llm_agent import parse_files, safe_write


def replay_agent(path, protected=()):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]

    def agent(goal, feedback, workdir):
        if not rows:
            raise ValueError("replay exhausted: the live run ended here")
        row = rows.pop(0)
        files = parse_files(row["response"])
        if not files:
            raise ValueError("recorded response had no parsable FILE blocks")
        for rel, content in files:
            safe_write(workdir, rel, content, protected)
    return agent
