#!/usr/bin/env python3
"""Lightweight operator UI server for IMP."""

from __future__ import annotations

import argparse
import json
import mimetypes
import pathlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"


def _load_dashboard():
    import importlib.util
    import sys

    path = ROOT / "core" / "imp-operator-dashboard.py"
    spec = importlib.util.spec_from_file_location("imp_operator_dashboard", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _status_payload() -> dict:
    dashboard = _load_dashboard()
    return dashboard.build_status_payload()


def _guess_type(path: pathlib.Path) -> str:
    mimetype, _ = mimetypes.guess_type(path.as_posix())
    return mimetype or "application/octet-stream"


class OperatorHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            payload = _status_payload()
            data = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path in ("/", "/index.html"):
            file_path = UI_DIR / "index.html"
        else:
            file_path = UI_DIR / parsed.path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _guess_type(file_path))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IMP operator UI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if not UI_DIR.exists():
        raise SystemExit(f"UI directory missing: {UI_DIR}")

    server = ThreadingHTTPServer((args.host, args.port), OperatorHandler)
    print(f"Operator UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
