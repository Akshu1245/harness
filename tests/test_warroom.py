"""War room server: real events.jsonl over HTTP, no demo data."""
import json
import pathlib
import sys
import threading
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rashi import warroom
from rashi.loop import run_loop


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read().decode()


def test_serves_page_and_real_events(tmp_path):
    spec = {"goal": "g", "workdir": str(tmp_path), "max_iters": 1,
            "checks": [{"id": "C1", "cmd": "true"}]}
    run_loop(spec, lambda g, f, w: None)
    srv = warroom.serve(str(tmp_path), port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        status, page = _get(f"http://127.0.0.1:{port}/")
        assert status == 200 and "EVENT STREAM" in page and "debateEvents" not in page
        status, body = _get(f"http://127.0.0.1:{port}/events")
        data = json.loads(body)
        assert data["live"] and [e["kind"] for e in data["events"]] == ["iter", "status"]
        assert data["events"][-1]["status"] == "DONE_VERIFIED"
    finally:
        srv.shutdown()


def test_events_endpoint_honest_when_no_data(tmp_path):
    srv = warroom.serve(str(tmp_path), port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        _, body = _get(f"http://127.0.0.1:{port}/events")
        assert json.loads(body) == {"events": [], "live": False}
    finally:
        srv.shutdown()
