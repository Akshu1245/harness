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


def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_approval_endpoints_round_trip_a_pending_spec(tmp_path):
    srv = warroom.serve(str(tmp_path), port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        _, data = _get(f"http://127.0.0.1:{port}/approval")
        assert json.loads(data)["pending"] is False
        # no pending approval -> a decision is refused, not recorded
        code, body = _post(f"http://127.0.0.1:{port}/decision", {"approve": True})
        assert code == 409 and body["ok"] is False
        (tmp_path / "PENDING_APPROVAL.json").write_text(json.dumps(
            {"mode": "review-and-accept", "spec": "s", "findings": []}))
        _, data = _get(f"http://127.0.0.1:{port}/approval")
        assert json.loads(data)["pending"] is True
        code, body = _post(f"http://127.0.0.1:{port}/decision", {"approve": True})
        assert code == 200 and body["ok"] is True
        assert json.loads((tmp_path / "APPROVAL_DECISION.json").read_text())["approve"] is True
    finally:
        srv.shutdown()


def test_page_offers_exactly_the_three_modes():
    page = (pathlib.Path(warroom.PAGE)).read_text()
    assert "full-access" in page and "review-and-accept" in page and "ask-for-everything" in page
