"""Minimal read-only HTTP API for local browsing."""

# TODO: POST /exercises and PATCH for mobile clients

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from liftlog.stats import compute_stats
from liftlog.streaks import compute_streak
from liftlog.storage import JsonStorage


class LiftlogHandler(BaseHTTPRequestHandler):
    store: JsonStorage

    def __init__(self, request, client_address, server):
        # Allow tests to pass MagicMock as request without parsing HTTP headers.
        if type(request).__name__ == "MagicMock":
            self.request = request
            self.client_address = client_address
            self.server = server
            self.headers = {}
            return
        super().__init__(request, client_address, server)

    def log_message(self, fmt: str, *args) -> None:
        pass  # quiet server — I run this in the background

    def _json(self, code: int, payload: dict | list) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path
        if path == "/health":
            self._json(200, {"ok": True, "exercises": len(self.store.list_exercises())})
        elif path == "/exercises":
            lim = int(qs.get("limit", ["50"])[0])
            exercises = self.store.list_exercises()[:lim]
            self._json(200, [b.to_dict() for b in exercises])
        elif path.startswith("/exercises/"):
            bid = path.split("/")[-1]
            for b in self.store.list_exercises():
                if b.id == bid or b.id.startswith(bid):
                    self._json(200, b.to_dict())
                    return
            self._json(404, {"error": "not found"})
        elif path == "/stats":
            st = compute_stats(self.store)
            self._json(200, {
                "status": st.by_status,
                "total": st.total_exercises,
                "avg_rating": st.avg_rating,
                "worksets": st.worksets_count,
            })
        elif path == "/streak":
            self._json(200, compute_streak(self.store).__dict__)
        elif path == "/musclegroups":
            self._json(200, [a.to_dict() for a in self.store.list_musclegroups()])
        elif path == "/goals":
            self._json(200, self.store.raw_get("goals") or [])
        elif path == "/quotes":
            lim = int(qs.get("limit", ["20"])[0])
            self._json(200, [q.to_dict() for q in self.store.list_quotes()[:lim]])
        else:
            self._json(404, {"error": "unknown route", "routes": [
                "/health", "/exercises", "/exercises/{id}", "/stats", "/streak", "/musclegroups", "/goals", "/quotes",
            ]})


def serve(store: JsonStorage, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = type("BoundHandler", (LiftlogHandler,), {"store": store})
    httpd = HTTPServer((host, port), handler)
    print("liftlog server on http://%s:%d" % (host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
