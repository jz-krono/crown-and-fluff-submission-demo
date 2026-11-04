#!/usr/bin/env python3
"""Run the independent Crown & Fluff submission demonstration on localhost."""

import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from meta_client import MetaError, key_from_environment
from workflow import RunEngine


ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    server_version = "CFLocalDemo/1"

    def log_message(self, fmt, *args):
        # Paths and incidental HTTP data are not business events or model receipts.
        pass

    def _send(self, status, data, content_type="application/json; charset=utf-8"):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(data)

    def _json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 4096 or size < 0:
            raise ValueError("Request exceeds 4 KiB")
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
            raise ValueError("Send application/json")
        value = json.loads(self.rfile.read(size) or b"{}")
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    def _origin_valid(self):
        origin = self.headers.get("Origin")
        return not origin or origin in ("http://127.0.0.1:" + str(self.server.server_port),
                                        "http://localhost:" + str(self.server.server_port))

    def do_GET(self):
        path = urlsplit(self.path).path
        engine = self.server.engine
        if path == "/":
            return self._send(200, (ROOT / "web/index.html").read_bytes(), "text/html; charset=utf-8")
        if path in ("/app.css", "/app.js"):
            file = ROOT / "web" / path[1:]
            return self._send(200, file.read_bytes(), mimetypes.guess_type(file)[0] or "text/plain")
        if path == "/api/config":
            try:
                key_from_environment()
                keyed = True
            except MetaError:
                keyed = False
            return self._send(200, {"keyConfigured": keyed, "mode": "LOCAL DEMO",
                                    "sourcePhoto": "examples/meta-source.jpg"})
        if path == "/api/runs":
            return self._send(200, engine.ledger.list())
        if path == "/api/source":
            return self._send(200, engine.photo.read_bytes(), "image/jpeg")
        if path == "/api/evidence":
            return self._send(200, json.loads((ROOT / "evidence/test-summary.json").read_text()))
        if path.startswith("/api/runs/"):
            parts = path.split("/")
            if len(parts) == 4:
                run = engine.ledger.get(parts[3])
                return self._send(200, run) if run else self._send(404, {"error": "Unknown run"})
            if len(parts) == 5 and parts[4] == "image":
                run = engine.ledger.get(parts[3])
                if not run or not run["image_file"]:
                    return self._send(404, {"error": "No generated image for this run"})
                image = Path(run["image_file"])
                if image.parent != engine.root / "assets" or not image.is_file():
                    return self._send(404, {"error": "Image unavailable"})
                return self._send(200, image.read_bytes(), "image/webp")
            if len(parts) == 5 and parts[4] == "email.eml":
                run = engine.ledger.get(parts[3])
                outbox = engine.root / "outbox" / (parts[3] + ".eml")
                if not run or not any(e["kind"] == "sample.email.outbox.created" for e in run["events"]) or not outbox.is_file():
                    return self._send(404, {"error": "No local email for this run"})
                return self._send(200, outbox.read_bytes(), "message/rfc822")
        return self._send(404, {"error": "Not found"})

    def do_POST(self):
        if not self._origin_valid():
            return self._send(403, {"error": "This app accepts requests from its own localhost page"})
        path = urlsplit(self.path).path
        engine = self.server.engine
        try:
            data = self._json()
            if path == "/api/runs":
                kind = data.get("kind", "live")
                if kind == "sample":
                    return self._send(201, {"id": engine.create_sample()})
                if kind in ("pack3", "pack5"):
                    return self._send(201, {"id": engine.create_pack_sample(int(kind[-1]))})
                if kind not in ("live", "pending") or type(data.get("consent", False)) is not bool:
                    raise ValueError("Invalid sample scenario")
                if kind == "live":
                    key_from_environment()  # validate before recording a run; value never enters the UI
                run_id = engine.create(paid=kind == "live", consent=data.get("consent", False))
                if kind == "live":
                    threading.Thread(target=engine.execute, args=(run_id,), daemon=True).start()
                return self._send(201, {"id": run_id})
            parts = path.split("/")
            if len(parts) == 5 and parts[:3] == ["", "api", "runs"]:
                run_id, action = parts[3:]
                if action == "duplicate-payment":
                    return self._send(200, {"newEffect": engine.apply_payment(run_id, "duplicate-event")})
                if action == "case":
                    engine.case(run_id)
                    return self._send(200, {"id": run_id})
                if action == "refund":
                    return self._send(200, {"newEffect": engine.operator_refund(
                        run_id, confirmed=data.get("confirmed") is True)})
            return self._send(404, {"error": "Not found"})
        except (ValueError, MetaError, KeyError, json.JSONDecodeError) as exc:
            return self._send(400, {"error": str(exc)[:200]})


def main():
    parser = argparse.ArgumentParser(description="Local worker, verifier and Recorder demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    engine = RunEngine(args.data_dir.resolve(), ROOT / "examples/meta-source.jpg")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.engine = engine
    print("Crown & Fluff local demo: http://127.0.0.1:" + str(args.port), flush=True)
    print("Local simulator; live Meta calls use MODEL_API_KEY from the shell or ignored .env", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
