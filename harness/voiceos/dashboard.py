"""Local read-only VoiceOS cognition dashboard event stream.

This is observability: states, timings, and final output. It intentionally does
not expose private hidden model reasoning or tool credentials. Localhost only.
"""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import threading
import time


class EventHub:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers = set()
        self._history = deque(maxlen=80)
        self._seq = 0

    def emit(self, stage, *, detail="", elapsed_ms=None, transient=False, **metrics):
        safe_detail = str(detail or "")[:180]
        with self._lock:
            self._seq += 1
            event = {"seq": self._seq, "at": time.time(), "stage": stage,
                     "detail": safe_detail, "elapsed_ms": elapsed_ms,
                     "metrics": metrics}
            if not transient:
                self._history.append(event)
            for subscriber in tuple(self._subscribers):
                try:
                    subscriber.put_nowait(event)
                except queue.Full:
                    # Prefer newest state instead of indefinitely queueing old frames.
                    try:
                        subscriber.get_nowait()
                        subscriber.put_nowait(event)
                    except queue.Empty:
                        pass
        return event

    def subscribe(self):
        sink = queue.Queue(maxsize=96)
        with self._lock:
            for event in self._history:
                sink.put_nowait(event)
            self._subscribers.add(sink)
        return sink

    def unsubscribe(self, sink):
        with self._lock:
            self._subscribers.discard(sink)


class Dashboard:
    def __init__(self, port=8765):
        self.hub = EventHub()
        self.port = port
        self.server = None

    def start(self):
        hub = self.hub
        ui_path = Path(__file__).with_name("dashboard.html")

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                # Avoid logging potentially sensitive query strings.
                return

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path == "/":
                    body = ui_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                    self.end_headers()
                    self.wfile.write(body)
                elif path == "/cortex3d.js":
                    body = ui_path.with_name("cortex3d.js").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/javascript; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)
                elif path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache, no-store")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()
                    sink = hub.subscribe()
                    try:
                        self.wfile.write(b": connected\n\n")
                        self.wfile.flush()
                        while True:
                            try:
                                event = sink.get(timeout=10)
                                payload = "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                            except queue.Empty:
                                payload = ": heartbeat\n\n"
                            self.wfile.write(payload.encode("utf-8"))
                            self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                        pass
                    finally:
                        hub.unsubscribe(sink)
                else:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True, name="ultron-dashboard").start()
        self.hub.emit("idle", detail="Cognitive visualization ready")
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def emit(self, stage, **kwargs):
        return self.hub.emit(stage, **kwargs)

    def audio_level(self, level, *, turn):
        # Ephemeral 20 Hz playback meter; never pollute reconnect history.
        return self.hub.emit("audio_level", transient=True, turn=turn,
                             level=round(max(0.0, min(1.0, float(level))), 3))

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
