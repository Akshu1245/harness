"""Tracing (gap B10): spans as events. Every phase emits span_start / span_end with a duration
and a parent link, so the war room or any downstream tool can reconstruct the run tree.
No Langfuse dependency (zero spend, works offline); the event shape maps onto span ingestion
later if a backend is ever added."""
import time
import uuid

from .loop import emit


class span:
    """with span(workdir, "spec_gate", parent=run_id): ... - emits start and end events.
    Never raises: a tracing bug must not break a run."""

    def __init__(self, workdir, name, parent=None, **fields):
        self.workdir, self.name, self.parent, self.fields = workdir, name, parent, fields
        self.id = uuid.uuid4().hex[:8]

    def __enter__(self):
        self.t0 = time.monotonic()
        try:
            emit(self.workdir, "span_start", span=self.id, name=self.name,
                 parent=self.parent, **self.fields)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            emit(self.workdir, "span_end", span=self.id, name=self.name,
                 duration_ms=int((time.monotonic() - self.t0) * 1000),
                 failed=exc_type is not None)
        except Exception:
            pass
        return False  # exceptions propagate; the span records them, never swallows them
