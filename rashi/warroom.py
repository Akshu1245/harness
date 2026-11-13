"""Serve the war room with the REAL event stream (events.jsonl) instead of demo data.

stdlib only (ponytail: no new dependency for a few lines). Usage:
    python -m rashi.warroom /path/to/workdir [port]
Then open http://127.0.0.1:8765/ - the page polls /events and shows DONE_VERIFIED/STOPPED
status exactly as the loop recorded it. Binds localhost; there is no auth, so no tunnel.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "data" / "visual_war_room.html"


def make_handler(workdir):
    events_path = Path(workdir) / "events.jsonl"
    pending_path = Path(workdir) / "PENDING_APPROVAL.json"
    decision_path = Path(workdir) / "APPROVAL_DECISION.json"

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype, code=200):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/events"):
                if not events_path.exists():
                    return self._send('{"events": [], "live": false}', "application/json")
                rows = []
                for line in events_path.read_text().splitlines()[-500:]:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
                return self._send(json.dumps({"events": rows, "live": True}), "application/json")
            if self.path.startswith("/approval"):
                if not pending_path.exists():
                    return self._send('{"pending": false}', "application/json")
                try:
                    data = json.loads(pending_path.read_text())
                except ValueError:
                    return self._send('{"pending": false}', "application/json")
                return self._send(json.dumps({"pending": True, **data}), "application/json")
            if self.path in ("/", "/index.html"):
                return self._send(PAGE.read_text(), "text/html")
            self._send("not found", "text/plain", 404)

        def do_POST(self):
            if self.path.startswith("/decision"):
                n = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    return self._send('{"ok": false}', "application/json", 400)
                # Only a genuinely pending approval can be decided; the page cannot approve thin air.
                if not pending_path.exists():
                    return self._send('{"ok": false, "error": "no pending approval"}',
                                      "application/json", 409)
                decision_path.write_text(json.dumps({"approve": bool(body.get("approve"))}))
                return self._send('{"ok": true}', "application/json")
            self._send("not found", "text/plain", 404)

        def log_message(self, *a):  # quiet
            pass

    return Handler


def serve(workdir, port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(workdir))


if __name__ == "__main__":
    wd = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    print(f"war room on http://127.0.0.1:{port}/  (events: {Path(wd).resolve() / 'events.jsonl'})")
    serve(wd, port).serve_forever()
