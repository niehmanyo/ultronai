#!/usr/bin/env python3
"""Private Mac-hosted Ultron remote chat API.

Binds to loopback by default. Use Tailscale Serve for remote HTTPS access.
All API routes require a bearer token; DSH calls are serialized because the
SDK runtime is a single shared process. No prompt/response content is logged.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HARNESS_ROOT = ROOT.parent
TOKEN_PATH = Path.home() / ".ultron" / "remote-access-token"
MAX_BODY = 24 * 1024
MAX_MESSAGE = 12_000
SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")


def load_or_create_token() -> str:
    TOKEN_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(TOKEN_PATH.parent, 0o700)
    except OSError:
        pass
    if TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if len(token) >= 40:
            return token
    token = secrets.token_urlsafe(48)
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write(token + "\n")
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
    return token


def load_api_key() -> str:
    value = os.getenv("OPENAI_API_KEY", "").strip()
    if value:
        return value
    if sys.platform == "darwin":
        import subprocess
        for service in ("com.ultron.voiceos.desktop", "com.ultron.remote.server"):
            try:
                result = subprocess.run(
                    ["security", "find-generic-password", "-s", service,
                     "-a", "OPENAI_API_KEY", "-w"],
                    capture_output=True, text=True, timeout=5, check=True,
                )
                value = result.stdout.strip()
                if value:
                    return value
            except (OSError, subprocess.SubprocessError):
                continue
    return ""


class RemoteApplication:
    def __init__(self, harness, token: str):
        self.harness = harness
        self.token = token
        self.lock = threading.Lock()
        self.turn = 0
        self.started_at = time.time()

    def authorized(self, handler) -> bool:
        header = handler.headers.get("Authorization", "")
        supplied = header[7:].strip() if header.startswith("Bearer ") else ""
        return bool(supplied) and hmac.compare_digest(supplied, self.token)

    def run_turn(self, message: str, session_id: str, send_event):
        from core import run_agent
        from tool_graph import ToolGraphObserver

        with self.lock:
            self.turn += 1
            turn = self.turn
            send_event({"type": "status", "stage": "thinking", "turn": turn})
            graph = ToolGraphObserver(
                lambda stage, **data: send_event({
                    "type": "tool", "stage": stage,
                    "tool_name": data.get("tool_name", "tool"),
                    "tool_state": data.get("tool_state", "running"),
                    "tool_id": data.get("tool_id"),
                }),
                turn=turn,
            )
            try:
                reply = run_agent(
                    self.harness, message, session_id,
                    reply_language="auto", on_notification=graph,
                )
                reply = (reply or "").strip()
                if not reply:
                    reply = "I completed the turn but received no final assistant message."
                send_event({"type": "final", "reply": reply[:20_000], "turn": turn})
            except Exception as exc:
                from core import safe_diagnostic
                send_event({"type": "error", "message": safe_diagnostic(exc)})
            finally:
                graph.finish()


def build_parser():
    parser = argparse.ArgumentParser(description="Private Ultron remote server for macOS")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind address; keep loopback and use Tailscale Serve for remote access")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--workspace", type=Path, default=HARNESS_ROOT / "ultron-workspace")
    parser.add_argument("--dsh-home", type=Path, default=Path.home() / ".ultron-dsh")
    parser.add_argument("--profile", default=os.getenv("ULTRON_VOICE_PROFILE", "sdk"))
    parser.add_argument("--provider", default=os.getenv("ULTRON_VOICE_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.getenv("ULTRON_VOICE_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--sdk-patch", type=Path, default=ROOT / "openai.patch.yml")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if sys.platform != "darwin":
        print("[Ultron Remote] This first version is macOS-only.", file=sys.stderr)
        return 2
    if not 1 <= args.port <= 65535:
        print("[Ultron Remote] Invalid port.", file=sys.stderr)
        return 2
    key = load_api_key()
    if not key:
        print("[Ultron Remote] OpenAI API key missing. Save it in Keychain or export OPENAI_API_KEY.", file=sys.stderr)
        return 2
    if not args.workspace.expanduser().is_dir():
        print("[Ultron Remote] Workspace directory missing:", args.workspace, file=sys.stderr)
        return 2
    if not args.sdk_patch.expanduser().is_file():
        print("[Ultron Remote] SDK patch missing:", args.sdk_patch, file=sys.stderr)
        return 2
    os.environ["OPENAI_API_KEY"] = key
    from core import configure_proxy
    configure_proxy()
    try:
        from deepseek_harness import DeepSeekHarness
    except (ImportError, OSError) as exc:
        print("[Ultron Remote] DSH SDK dependency unavailable:", type(exc).__name__, file=sys.stderr)
        return 2

    token = load_or_create_token()
    app = None
    html_path = ROOT / "remote.html"
    manifest = {
        "name": "Ultron Remote", "short_name": "Ultron",
        "start_url": "/", "display": "standalone",
        "background_color": "#030b15", "theme_color": "#061827",
        "icons": []
    }

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            # Never log request bodies, query strings, tokens or prompts.
            return

        def headers_out(self, status=200, content_type="application/json; charset=utf-8",
                        length=None, cache="no-store"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                             "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
                             "frame-ancestors 'none'; form-action 'self'")
            if length is not None:
                self.send_header("Content-Length", str(length))
            self.end_headers()

        def json_response(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.headers_out(status, length=len(body))
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                body = html_path.read_bytes()
                self.headers_out(200, "text/html; charset=utf-8", len(body))
                self.wfile.write(body)
                return
            if path == "/sw.js":
                body = (ROOT / "remote_sw.js").read_bytes()
                self.headers_out(200, "text/javascript; charset=utf-8", len(body), cache="no-cache")
                self.wfile.write(body)
                return
            if path == "/manifest.webmanifest":
                body = json.dumps(manifest).encode()
                self.headers_out(200, "application/manifest+json", len(body))
                self.wfile.write(body)
                return
            if path == "/api/health":
                if not app.authorized(self):
                    self.json_response(401, {"error": "unauthorized"})
                    return
                self.json_response(200, {
                    "status": "online", "service": "Ultron Remote",
                    "uptime_seconds": int(time.time() - app.started_at),
                    "model": args.model, "active_turns": int(app.lock.locked()),
                })
                return
            self.json_response(404, {"error": "not_found"})

        def do_POST(self):
            if urlparse(self.path).path != "/api/chat":
                self.json_response(404, {"error": "not_found"})
                return
            if not app.authorized(self):
                self.json_response(401, {"error": "unauthorized"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.json_response(400, {"error": "invalid_content_length"})
                return
            if length < 1 or length > MAX_BODY:
                self.json_response(413, {"error": "request_too_large"})
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.json_response(400, {"error": "invalid_json"})
                return
            if not isinstance(payload, dict):
                self.json_response(400, {"error": "invalid_request"})
                return
            message = payload.get("message")
            session_id = payload.get("session_id")
            if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE:
                self.json_response(400, {"error": "message_must_be_1_to_12000_chars"})
                return
            if not isinstance(session_id, str) or not SESSION_RE.fullmatch(session_id):
                self.json_response(400, {"error": "invalid_session_id"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()

            def send(event):
                data = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                self.wfile.write(("data: " + data + "\n\n").encode("utf-8"))
                self.wfile.flush()

            try:
                send({"type": "status", "stage": "queued"})
                app.run_turn(message.strip(), session_id, send)
                send({"type": "done"})
            except (BrokenPipeError, ConnectionResetError, OSError):
                # Agent work may already be running; SDK call cannot be safely cancelled.
                pass

    configure_proxy()
    try:
        from deepseek_harness import DeepSeekHarness
        print("[Ultron Remote] Initializing DSH Agent runtime…", flush=True)
        with DeepSeekHarness(
            dsh_home=str(args.dsh_home.expanduser().resolve()),
            cwd=str(args.workspace.expanduser().resolve()),
            profile=args.profile, patches=(str(args.sdk_patch.expanduser().resolve()),),
            provider=args.provider, model=args.model,
        ) as harness:
            app = RemoteApplication(harness, token)
            server = ThreadingHTTPServer((args.host, args.port), Handler)
            server.daemon_threads = True
            print(f"[Ultron Remote] Listening: http://{args.host}:{server.server_address[1]}", flush=True)
            print(f"[Ultron Remote] Access token file: {TOKEN_PATH}", flush=True)
            print("[Ultron Remote] Token (enter once in the phone web app):", token, flush=True)
            print("[Ultron Remote] Keep this server private. Use Tailscale Serve for remote HTTPS.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\n[Ultron Remote] Shutting down…", flush=True)
            finally:
                server.shutdown()
                server.server_close()
    except OSError as exc:
        print("[Ultron Remote] Server failed:", type(exc).__name__, file=sys.stderr)
        return 1
    except Exception as exc:
        from core import safe_diagnostic
        print("[Ultron Remote] DSH initialization failed:", safe_diagnostic(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
