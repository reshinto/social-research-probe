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
    """Get default Voicebox API base from config.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _default_voicebox_base()
        Output:
            "http://127.0.0.1:5050"
    """
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
    """Point the embedded report toolbar at the local same-origin proxy.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        html_text: HTML document text being rewritten or sent to the browser.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _rewrite_report_html(
                html_text="AI safety",
            )
        Output:
            "<section>Summary</section>"
    """
    return _API_BASE_ATTR_RE.sub(
        f'data-api-base="{_VOICEBOX_PROXY_PREFIX}"', html_text, count=_API_BASE_SUBSTITUTION_COUNT
    )


def _proxy_timeout_seconds(path: str) -> int:
    """Return the Voicebox proxy timeout for *path*.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _proxy_timeout_seconds(
                path=Path("report.html"),
            )
        Output:
            180
    """
    if path.endswith(_VOICEBOX_STREAM_ENDPOINT):
        return _STREAM_PROXY_TIMEOUT_SECONDS
    return _DEFAULT_PROXY_TIMEOUT_SECONDS


def _send_html_response(handler: BaseHTTPRequestHandler, html_text: str) -> None:
    """Send HTML response with proper headers.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        handler: Active HTTP handler with request data and a writable response stream.
        html_text: HTML document text being rewritten or sent to the browser.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _send_html_response(
                handler=handler,
                html_text="AI safety",
            )
        Output:
            None
    """
    content = html_text.encode("utf-8")
    handler.send_response(_HTTP_OK)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def _send_file_response(handler: BaseHTTPRequestHandler, file_path: Path) -> None:
    """Send file response with proper headers.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        handler: Active HTTP handler with request data and a writable response stream.
        file_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _send_file_response(
                handler=handler,
                file_path=Path("report.html"),
            )
        Output:
            None
    """
    payload = file_path.read_bytes()
    handler.send_response(_HTTP_OK)
    handler.send_header("Content-Type", _guess_content_type(file_path))
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _resolve_safe_local_file(request_path: str, report_dir: Path) -> Path | None:
    """Resolve local file path, ensure it's within report directory.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        request_path: Filesystem location used to read, write, or resolve project data.
        report_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _resolve_safe_local_file(
                request_path=Path("report.html"),
                report_dir=Path(".skill-data"),
            )
        Output:
            Path("report.html")
    """
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
    """Proxy request to Voicebox API.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        handler: Active HTTP handler with request data and a writable response stream.
        proxy_base: Voicebox server URL used by the same-origin proxy.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _proxy_voicebox_request(
                handler=handler,
                proxy_base="AI safety",
            )
        Output:
            None
    """
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


def _serve_report_get(
    handler: BaseHTTPRequestHandler,
    *,
    report_file: Path,
    report_dir: Path,
    report_url_path: str,
    proxy_base: str,
) -> None:
    """Keep GET routing small enough that report serving rules stay visible.

    Args:
        handler: Active HTTP handler with request data and a writable response stream.
        report_file: Resolved HTML report served for ``/`` and by filename.
        report_dir: Directory that asset requests must stay inside.
        report_url_path: Browser-visible URL path for the selected report filename.
        proxy_base: Voicebox server URL used for same-origin proxy calls.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _serve_report_get(
                handler=handler,
                report_file=Path("out/report.html"),
                report_dir=Path("out"),
                report_url_path="/report.html",
                proxy_base="http://127.0.0.1:5050",
            )
        Output:
            None
    """
    path = urlsplit(handler.path).path
    if path in {_ROOT_PATH, report_url_path}:
        _send_html_response(handler, _rewrite_report_html(report_file.read_text(encoding="utf-8")))
        return
    if path.startswith(_VOICEBOX_PROXY_PREFIX):
        _proxy_voicebox_request(handler, proxy_base)
        return
    local_file = _resolve_safe_local_file(path, report_dir)
    if local_file is not None:
        _send_file_response(handler, local_file)
        return
    handler.send_error(_HTTP_NOT_FOUND, "Not Found")


def _serve_report_post(handler: BaseHTTPRequestHandler, *, proxy_base: str) -> None:
    """Allow report toolbar POST calls only when they are meant for Voicebox.

    Command helpers keep user-facing parsing, validation, and output formatting out of pipeline and
    service code.

    Args:
        handler: Active HTTP handler with request data and a writable response stream.
        proxy_base: Voicebox server URL used for same-origin proxy calls.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _serve_report_post(
                handler=handler,
                proxy_base="http://127.0.0.1:5050",
            )
        Output:
            None
    """
    path = urlsplit(handler.path).path
    if path.startswith(_VOICEBOX_PROXY_PREFIX):
        _proxy_voicebox_request(handler, proxy_base)
        return
    handler.send_error(_HTTP_NOT_FOUND, "Not Found")


class _ReportHandler(BaseHTTPRequestHandler):
    """Base handler whose class attributes bind it to one report server instance.

    The HTTP server API instantiates handlers without custom constructor arguments, so the factory
    below creates a small subclass with the selected report path and proxy settings attached at the
    class level.

    Examples:
        Input:
            _ReportHandler
        Output:
            A request handler type ready to be bound by ``_make_handler``.
    """

    report_file: Path
    report_dir: Path
    report_url_path: str
    proxy_base: str

    def log_message(self, format: str, *args: object) -> None:
        """Keep local report serving quiet unless the code writes an explicit error.

        Args:
            format: Standard BaseHTTPRequestHandler log format string.

        Returns:
            None. The default access-log line is intentionally suppressed.

        Examples:
            Input:
                log_message(
                    format='"GET /report.html HTTP/1.1" 200 -',
                )
            Output:
                None
        """
        return

    def do_GET(self) -> None:
        """Serve the report document, report assets, or a proxied Voicebox GET request.

        Returns:
            None. The handler writes the response body or sends a 404 before returning.

        Examples:
            Input:
                do_GET()
            Output:
                None
        """
        _serve_report_get(
            self,
            report_file=self.report_file,
            report_dir=self.report_dir,
            report_url_path=self.report_url_path,
            proxy_base=self.proxy_base,
        )

    def do_POST(self) -> None:
        """Forward Voicebox POST requests while rejecting unsupported local POST paths.

        Returns:
            None. The handler writes the proxied response or sends a 404 before returning.

        Examples:
            Input:
                do_POST()
            Output:
                None
        """
        _serve_report_post(self, proxy_base=self.proxy_base)


def _make_handler(
    report_path: Path,
    voicebox_base: str,
) -> type[BaseHTTPRequestHandler]:
    """Build the HTTP request handler bound to the selected report and Voicebox proxy settings.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report_path: HTML report file that should be available at ``/`` and by filename.
        voicebox_base: Voicebox server URL that browser toolbar calls should proxy to.

    Returns:
        Handler subclass with report and proxy settings attached as class attributes.

    Examples:
        Input:
            _make_handler(
                report_path=Path("report.html"),
                voicebox_base="http://127.0.0.1:5050",
            )
        Output:
            A BaseHTTPRequestHandler subclass bound to ``report.html``.
    """
    report_file = report_path.resolve()
    return type(
        "_BoundReportHandler",
        (_ReportHandler,),
        {
            "report_file": report_file,
            "report_dir": report_file.parent,
            "report_url_path": f"/{report_file.name}",
            "proxy_base": voicebox_base.rstrip("/"),
        },
    )


def _guess_content_type(path: Path) -> str:
    """Return a deterministic content type for *path*.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _guess_content_type(
                path=Path("report.html"),
            )
        Output:
            "AI safety"
    """
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
    """Build the server structure consumed by the next step.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.
        host: Local interface address that the report server should bind to.
        port: Count, database id, index, or limit that bounds the work being performed.
        voicebox_base: Voicebox server URL used by report audio controls.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_server(
                report_path=Path("report.html"),
                host="AI safety",
                port=3,
                voicebox_base="AI safety",
            )
        Output:
            "AI safety"
    """
    return ThreadingHTTPServer((host, port), _make_handler(report_path, voicebox_base))


def _resolve_report_file(report_path: str) -> Path:
    """Resolve and validate report file path.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _resolve_report_file(
                report_path=Path("report.html"),
            )
        Output:
            Path("report.html")
    """
    resolved = Path(report_path).expanduser().resolve()
    if not resolved.is_file():
        raise ValidationError(f"report file not found: {report_path}")
    return resolved


def _get_proxy_target(voicebox_base: str | None) -> str:
    """Get Voicebox proxy target from arg, env var, or config default.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        voicebox_base: Voicebox server URL used by report audio controls.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _get_proxy_target(
                voicebox_base="AI safety",
            )
        Output:
            "AI safety"
    """
    return voicebox_base or os.environ.get("SRP_VOICEBOX_API_BASE") or _default_voicebox_base()


def _start_and_run_server(
    report_path: Path,
    host: str,
    port: int,
    proxy_target: str,
) -> None:
    """Start server, run it, and clean up on exit.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.
        host: Local interface address that the report server should bind to.
        port: Count, database id, index, or limit that bounds the work being performed.
        proxy_target: Voicebox URL chosen from CLI, environment, or config.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _start_and_run_server(
                report_path=Path("report.html"),
                host="AI safety",
                port=3,
                proxy_target="AI safety",
            )
        Output:
            None
    """
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
    """Serve *report_path* over local HTTP and proxy Voicebox on the same origin.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.
        host: Local interface address that the report server should bind to.
        port: Count, database id, index, or limit that bounds the work being performed.
        voicebox_base: Voicebox server URL used by report audio controls.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                report_path=Path("report.html"),
                host="AI safety",
                port=3,
                voicebox_base="AI safety",
            )
        Output:
            5
    """
    resolved_report = _resolve_report_file(report_path)
    proxy_target = _get_proxy_target(voicebox_base)
    _start_and_run_server(resolved_report, host, port, proxy_target)
    return ExitCode.SUCCESS
