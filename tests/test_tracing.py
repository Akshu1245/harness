import json
import pytest
from rashi.tracing import span


def test_span_measures_work_and_records_exception(tmp_path, monkeypatch):
    ticks = iter([10.0, 10.125])
    monkeypatch.setattr('rashi.tracing.time.monotonic', lambda: next(ticks))
    with pytest.raises(RuntimeError):
        with span(str(tmp_path), 'work'):
            raise RuntimeError('test')
    events = [json.loads(s) for s in (tmp_path / 'events.jsonl').read_text().splitlines()]
    assert events[-1]['duration_ms'] == 125
    assert events[-1]['failed'] is True
    assert events[0]['span'] == events[-1]['span']


def test_pipeline_loop_events_are_inside_loop_span(tmp_path):
    from rashi.pipeline import run_pipeline
    def llm(system, user):
        return '{"findings":[]}' if 'fresh reviewer' in system else 'Checks\n- `true`\n'
    run_pipeline('g', str(tmp_path), llm, lambda g, f, w: None, lambda s, f: True)
    events = [json.loads(s) for s in (tmp_path / 'events.jsonl').read_text().splitlines()]
    start = next(i for i,e in enumerate(events) if e['kind']=='span_start' and e['name']=='run_loop')
    end = next(i for i,e in enumerate(events) if e['kind']=='span_end' and e['name']=='run_loop')
    assert any(e['kind']=='iter' for e in events[start+1:end])
    assert any(e['kind']=='status' for e in events[start+1:end])
