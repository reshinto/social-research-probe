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

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000


def _default_voicebox_base() -> str:
    """Get default Voicebox API base from config."""
    from social_research_probe.config import load_active_config

    return load_active_config().voicebox["api_base"]


_DEFAULT_PROXY_TIMEOUT_SECONDS = 180
_STREAM_PROXY_TIMEOUT_SECONDS = 120
_API_BASE_ATTR_RE = re.compile(r'data-api-base="[^"]*"')

# HTTP routes
_VOICEBOX_PROXY_PREFIX = "/voicebox/"
_VOICEBOX_STREAM_ENDPOINT = "/generate/stream"
_ROOT_PATH = "/"

# HTTP status codes
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_HTTP_BAD_GATEWAY = 502

# Content types
_CONTENT_TYPE_WAV = "audio/wav"
_CONTENT_TYPE_MP3 = "audio/mpeg"
_CONTENT_TYPE_DEFAULT = "application/octet-stream"

# Request/response
_NO_CONTENT_LENGTH_STR = "0"
_API_BASE_SUBSTITUTION_COUNT = 1


def _rewrite_report_html(html_text: str) -> str:
    """Point the embedded report toolbar at the local same-origin proxy."""
    return _API_BASE_ATTR_RE.sub(
        f'data-api-base="{_VOICEBOX_PROXY_PREFIX}"', html_text, count=_API_BASE_SUBSTITUTION_COUNT
    )


def _proxy_timeout_seconds(path: str) -> int:
    """Return the Voicebox proxy timeout for *path*."""
    if path.endswith(_VOICEBOX_STREAM_ENDPOINT):
        return _STREAM_PROXY_TIMEOUT_SECONDS
    return _DEFAULT_PROXY_TIMEOUT_SECONDS


def _send_html_response(handler: BaseHTTPRequestHandler, html_text: str) -> None:
    """Send HTML response with proper headers."""
    content = html_text.encode("utf-8")
    handler.send_response(_HTTP_OK)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def _send_file_response(handler: BaseHTTPRequestHandler, file_path: Path) -> None:
    """Send file response with proper headers."""
    payload = file_path.read_bytes()
    handler.send_response(_HTTP_OK)
    handler.send_header("Content-Type", _guess_content_type(file_path))
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _resolve_safe_local_file(request_path: str, report_dir: Path) -> Path | None:
    """Resolve local file path, ensure it's within report directory."""
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


def _proxy_voicebox_request(handler: BaseHTTPRequestHandler, proxy_base: str) -> None:
    """Proxy request to Voicebox API."""
    target = proxy_base + handler.path.removeprefix(_VOICEBOX_PROXY_PREFIX)
    length = int(
        handler.headers.get("Content-Length", _NO_CONTENT_LENGTH_STR) or _NO_CONTENT_LENGTH_STR
    )
    body = handler.rfile.read(length) if length else None
    headers = {}
    for name in ("Content-Type", "Accept", "Range"):
        value = handler.headers.get(name)
        if value:
            headers[name] = value
    req = urllib.request.Request(target, data=body, headers=headers, method=handler.command)
    try:
        with urllib.request.urlopen(req, timeout=_proxy_timeout_seconds(target)) as resp:
            payload = resp.read()
            handler.send_response(resp.status)
            content_type = resp.headers.get("Content-Type", _CONTENT_TYPE_DEFAULT)
            handler.send_header("Content-Type", content_type)
            handler.send_header("Content-Length", str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        handler.send_response(exc.code)
        content_type = exc.headers.get("Content-Type", "text/plain; charset=utf-8")
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)
    except urllib.error.URLError as exc:
        payload = f"Voicebox proxy error: {exc.reason}".encode()
        handler.send_response(_HTTP_BAD_GATEWAY)
        handler.send_header("Content-Type", "text/plain; charset=utf-8")
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)


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
            if path in {_ROOT_PATH, report_url_path}:
                _send_html_response(
                    self, _rewrite_report_html(report_file.read_text(encoding="utf-8"))
                )
                return
            if path.startswith(_VOICEBOX_PROXY_PREFIX):
                _proxy_voicebox_request(self, proxy_base)
                return
            local_file = _resolve_safe_local_file(path, report_dir)
            if local_file is not None:
                _send_file_response(self, local_file)
                return
            self.send_error(_HTTP_NOT_FOUND, "Not Found")

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path.startswith(_VOICEBOX_PROXY_PREFIX):
                _proxy_voicebox_request(self, proxy_base)
                return
            self.send_error(_HTTP_NOT_FOUND, "Not Found")

    return _Handler


def _guess_content_type(path: Path) -> str:
    """Return a deterministic content type for *path*."""
    if path.suffix == ".wav":
        return _CONTENT_TYPE_WAV
    if path.suffix == ".mp3":
        return _CONTENT_TYPE_MP3
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or _CONTENT_TYPE_DEFAULT


def _build_server(
    report_path: Path,
    host: str,
    port: int,
    voicebox_base: str,
) -> ThreadingHTTPServer:
    """Create the local report server with Voicebox reverse-proxy routes."""
    return ThreadingHTTPServer((host, port), _make_handler(report_path, voicebox_base))


def _resolve_report_file(report_path: str) -> Path:
    """Resolve and validate report file path."""
    resolved = Path(report_path).expanduser().resolve()
    if not resolved.is_file():
        raise ValidationError(f"report file not found: {report_path}")
    return resolved


def _get_proxy_target(voicebox_base: str | None) -> str:
    """Get Voicebox proxy target from arg, env var, or config default."""
    return voicebox_base or os.environ.get("SRP_VOICEBOX_API_BASE") or _default_voicebox_base()


def _start_and_run_server(
    report_path: Path,
    host: str,
    port: int,
    proxy_target: str,
) -> None:
    """Start server, run it, and clean up on exit."""
    try:
        server = _build_server(report_path, host, port, proxy_target)
    except OSError as exc:
        raise ValidationError(f"cannot start report server on {host}:{port}: {exc}") from exc

    actual_host, actual_port = server.server_address[:2]
    print(f"[srp] Report server: http://{actual_host}:{actual_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def run(
    report_path: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    voicebox_base: str | None = None,
) -> int:
    """Serve *report_path* over local HTTP and proxy Voicebox on the same origin."""
    resolved_report = _resolve_report_file(report_path)
    proxy_target = _get_proxy_target(voicebox_base)
    _start_and_run_server(resolved_report, host, port, proxy_target)
    return ExitCode.SUCCESS
