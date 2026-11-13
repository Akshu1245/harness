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
            if self.path in ("/", "/index.html"):
                return self._send(PAGE.read_text(), "text/html")
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
