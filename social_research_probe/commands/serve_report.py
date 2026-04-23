"""Serve one HTML report over local HTTP and proxy Voicebox requests.

This avoids browser CORS failures when the report is opened from ``file://``
and needs to call a loopback Voicebox API on another port.
"""

from __future__ import annotations

import mimetypes
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from social_research_probe.errors import ValidationError

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_DEFAULT_VOICEBOX_BASE = "http://127.0.0.1:17493"
_DEFAULT_PROXY_TIMEOUT_SECONDS = 180
_STREAM_PROXY_TIMEOUT_SECONDS = 120
_API_BASE_ATTR_RE = re.compile(r'data-api-base="[^"]*"')


def _rewrite_report_html(html_text: str) -> str:
    """Point the embedded report toolbar at the local same-origin proxy."""
    return _API_BASE_ATTR_RE.sub('data-api-base="/voicebox"', html_text, count=1)


def _proxy_timeout_seconds(path: str) -> int:
    """Return the Voicebox proxy timeout for *path*."""
    if path.endswith("/generate/stream"):
        return _STREAM_PROXY_TIMEOUT_SECONDS
    return _DEFAULT_PROXY_TIMEOUT_SECONDS


def _make_handler(
    report_path: Path,
    voicebox_base: str,
) -> type[BaseHTTPRequestHandler]:
    """Create the request handler class for one report file + Voicebox target."""
    report_file = report_path.resolve()
    report_dir = report_file.parent
    report_url_path = f"/{report_file.name}"
    proxy_base = voicebox_base.rstrip("/")

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path in {"/", report_url_path}:
                self._serve_report()
                return
            if path.startswith("/voicebox/"):
                self._proxy_request()
                return
            local_file = self._resolve_local_file(path)
            if local_file is not None:
                self._serve_local_file(local_file)
                return
            self.send_error(404, "Not Found")

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path.startswith("/voicebox/"):
                self._proxy_request()
                return
            self.send_error(404, "Not Found")

        def _serve_report(self) -> None:
            content = _rewrite_report_html(report_file.read_text(encoding="utf-8")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _resolve_local_file(self, request_path: str) -> Path | None:
            relative = unquote(request_path).lstrip("/")
            if not relative:
                return None
            candidate = (report_dir / relative).resolve()
            try:
                candidate.relative_to(report_dir)
            except ValueError:
                return None
            if candidate.is_file():
                return candidate
            return None

        def _serve_local_file(self, file_path: Path) -> None:
            payload = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _guess_content_type(file_path))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _proxy_request(self) -> None:
            target = proxy_base + self.path.removeprefix("/voicebox")
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else None
            headers = {}
            for name in ("Content-Type", "Accept", "Range"):
                value = self.headers.get(name)
                if value:
                    headers[name] = value
            req = urllib.request.Request(target, data=body, headers=headers, method=self.command)
            try:
                with urllib.request.urlopen(req, timeout=_proxy_timeout_seconds(target)) as resp:
                    payload = resp.read()
                    self.send_response(resp.status)
                    content_type = resp.headers.get("Content-Type", "application/octet-stream")
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                self.send_response(exc.code)
                content_type = exc.headers.get("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except urllib.error.URLError as exc:
                payload = f"Voicebox proxy error: {exc.reason}".encode()
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

    return _Handler


def _guess_content_type(path: Path) -> str:
    """Return a deterministic content type for *path*."""
    if path.suffix == ".wav":
        return "audio/wav"
    if path.suffix == ".mp3":
        return "audio/mpeg"
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def _build_server(
    report_path: Path,
    host: str,
    port: int,
    voicebox_base: str,
) -> ThreadingHTTPServer:
    """Create the local report server with Voicebox reverse-proxy routes."""
    return ThreadingHTTPServer((host, port), _make_handler(report_path, voicebox_base))


def run(
    report_path: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    voicebox_base: str | None = None,
) -> int:
    """Serve *report_path* over local HTTP and proxy Voicebox on the same origin."""
    resolved_report = Path(report_path).expanduser().resolve()
    if not resolved_report.is_file():
        raise ValidationError(f"report file not found: {report_path}")

    proxy_target = (
        voicebox_base or os.environ.get("SRP_VOICEBOX_API_BASE") or _DEFAULT_VOICEBOX_BASE
    )
    try:
        server = _build_server(resolved_report, host, port, proxy_target)
    except OSError as exc:
        raise ValidationError(f"cannot start report server on {host}:{port}: {exc}") from exc

    actual_host, actual_port = server.server_address[:2]
    print(f"[srp] Report server: http://{actual_host}:{actual_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
