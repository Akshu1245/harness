"""Second brain (R29): a per-workdir, append-only memory the harness writes as it works and
reads back as context for the next brainstorm/spec. Deterministic, stdlib, no LLM summarizing
(no spend, no drift): the loop records what HAPPENED (done, rollback, tamper, stalls) and
recall returns the most recent records, capped, oldest first.

Store: .rashi/memory.jsonl - already excluded from tree snapshots and rollback stashes."""
import json
import time
from pathlib import Path

STORE = ("rashi", "memory.jsonl")  # under .rashi/ via Path(workdir, ".rashi", ...)


def remember(workdir, kind, text):
    """Append one record. kind: done | rollback | tamper | stall | note."""
    path = Path(workdir) / ".rashi" / "memory.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"ts": time.time(), "kind": kind, "text": text[:500]}) + "\n")


def recall(workdir, max_chars=2000, max_records=50):
    """Most recent records as one text block for prompt context; empty string when no memory."""
    path = Path(workdir) / ".rashi" / "memory.jsonl"
    if not path.is_file():
        return ""
    records = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue  # a corrupt line is skipped, never fatal
        if isinstance(r, dict) and r.get("kind") and r.get("text"):
            records.append(r)
    records = records[-max_records:]
    out = "\n".join(f"[{r['kind']}] {r['text']}" for r in records)
    if len(out) > max_chars:
        out = "[older records dropped]\n" + out[-max_chars:]
    return out
