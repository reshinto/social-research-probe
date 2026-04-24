"""Tests for the local report server + Voicebox proxy command."""

from __future__ import annotations

import io
import urllib.error
import urllib.request

import pytest
from social_research_probe.errors import ValidationError

import social_research_probe.commands.serve_report as serve_report_cmd


class _FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _invoke_handler(
    handler_cls: type,
    *,
    method: str,
    path: str,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    header_map = dict(headers or {})
    if body and "Content-Length" not in header_map:
        header_map["Content-Length"] = str(len(body))

    handler = object.__new__(handler_cls)
    handler.path = path
    handler.command = method
    handler.headers = header_map
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()

    state: dict[str, object] = {"status": None, "headers": {}}

    def send_response(code: int) -> None:
        state["status"] = code

    def send_header(name: str, value: str) -> None:
        state["headers"][name] = value

    def end_headers() -> None:
        return

    def send_error(code: int, message: str) -> None:
        state["status"] = code
        handler.wfile.write(f"{code} {message}".encode())

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers
    handler.send_error = send_error

    if method == "GET":
        handler.do_GET()
    else:
        handler.do_POST()

    return int(state["status"]), dict(state["headers"]), handler.wfile.getvalue()


def test_rewrite_report_html_swaps_voicebox_api_base():
    html = '<div id="tts-bar" data-api-base="http://127.0.0.1:17493"></div>'
    assert 'data-api-base="/voicebox"' in serve_report_cmd._rewrite_report_html(html)


def test_rewrite_report_html_leaves_non_matching_html_alone():
    html = "<html><body>No toolbar</body></html>"
    assert serve_report_cmd._rewrite_report_html(html) == html


def test_make_handler_serves_rewritten_report_and_proxies_voicebox(tmp_path, monkeypatch):
    report = tmp_path / "report.html"
    companion_audio = tmp_path / "report.voicebox.wav"
    companion_audio.write_bytes(b"wavlocal")
    report.write_text(
        '<!DOCTYPE html><html><body><div id="tts-bar" data-api-base="http://127.0.0.1:17493"></div></body></html>',
        encoding="utf-8",
    )
    requests: list[tuple[str, str, bytes | None, int]] = []

    def fake_urlopen(req, timeout):
        data = getattr(req, "data", None)
        requests.append((req.method, req.full_url, data, timeout))
        if req.full_url.endswith("/profiles"):
            return _FakeResponse(200, {"Content-Type": "application/json"}, b'[{"id":"voice-1"}]')
        if req.full_url.endswith("/generate/stream"):
            return _FakeResponse(200, {"Content-Type": "audio/wav"}, b"wavbytes")
        if req.full_url.endswith("/generate"):
            return _FakeResponse(200, {"Content-Type": "application/json"}, b'{"id":"gen-123"}')
        if req.full_url.endswith("/audio/gen-123"):
            return _FakeResponse(200, {"Content-Type": "audio/mpeg"}, b"mp3bytes")
        raise urllib.error.HTTPError(
            req.full_url,
            404,
            "Not Found",
            {"Content-Type": "text/plain; charset=utf-8"},
            io.BytesIO(b"nope"),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    handler_cls = serve_report_cmd._make_handler(report, "http://voicebox.local:17493")

    status, headers, body = _invoke_handler(handler_cls, method="GET", path="/")
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert 'data-api-base="/voicebox"' in body.decode("utf-8")

    status, headers, body = _invoke_handler(handler_cls, method="GET", path="/report.html")
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"

    status, headers, body = _invoke_handler(
        handler_cls,
        method="GET",
        path="/report.voicebox.wav",
    )
    assert status == 200
    assert headers["Content-Type"] == "audio/wav"
    assert body == b"wavlocal"

    status, headers, body = _invoke_handler(handler_cls, method="GET", path="/voicebox/profiles")
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert body == b'[{"id":"voice-1"}]'

    status, headers, body = _invoke_handler(
        handler_cls,
        method="POST",
        path="/voicebox/generate/stream",
        body=b'{"text":"hello"}',
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    assert headers["Content-Type"] == "audio/wav"
    assert body == b"wavbytes"

    status, headers, body = _invoke_handler(
        handler_cls,
        method="POST",
        path="/voicebox/generate",
        body=b'{"text":"hello"}',
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    assert body == b'{"id":"gen-123"}'

    status, headers, body = _invoke_handler(
        handler_cls,
        method="GET",
        path="/voicebox/audio/gen-123",
    )
    assert status == 200
    assert headers["Content-Type"] == "audio/mpeg"
    assert body == b"mp3bytes"

    status, _, body = _invoke_handler(handler_cls, method="GET", path="/missing")
    assert status == 404
    assert b"404 Not Found" in body

    status, headers, body = _invoke_handler(handler_cls, method="GET", path="/voicebox/missing")
    assert status == 404
    assert headers["Content-Type"] == "text/plain; charset=utf-8"
    assert body == b"nope"

    status, _, body = _invoke_handler(handler_cls, method="POST", path="/not-proxy", body=b"x")
    assert status == 404
    assert b"404 Not Found" in body

    assert requests == [
        ("GET", "http://voicebox.local:17493/profiles", None, 180),
        ("POST", "http://voicebox.local:17493/generate/stream", b'{"text":"hello"}', 120),
        ("POST", "http://voicebox.local:17493/generate", b'{"text":"hello"}', 180),
        ("GET", "http://voicebox.local:17493/audio/gen-123", None, 180),
        ("GET", "http://voicebox.local:17493/missing", None, 180),
    ]


def test_make_handler_returns_502_when_voicebox_is_unreachable(tmp_path, monkeypatch):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")

    def boom(req, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    handler_cls = serve_report_cmd._make_handler(report, "http://voicebox.local:17493")

    status, headers, body = _invoke_handler(handler_cls, method="GET", path="/voicebox/profiles")
    assert status == 502
    assert headers["Content-Type"] == "text/plain; charset=utf-8"
    assert b"connection refused" in body


def test_make_handler_rejects_report_dir_traversal(tmp_path):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")
    outside = tmp_path.parent / "outside.wav"
    outside.write_bytes(b"nope")

    handler_cls = serve_report_cmd._make_handler(report, "http://voicebox.local:17493")
    status, _, body = _invoke_handler(handler_cls, method="GET", path="/../outside.wav")
    assert status == 404
    assert b"404 Not Found" in body


def test_guess_content_type_uses_fallbacks(tmp_path):
    ogg = tmp_path / "clip.ogg"
    unknown = tmp_path / "clip.data"
    assert serve_report_cmd._guess_content_type(ogg) == "audio/ogg"
    assert serve_report_cmd._guess_content_type(unknown) == "application/octet-stream"


def test_build_server_constructs_threading_http_server(tmp_path, monkeypatch):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")

    class _FakeHttpServer:
        def __init__(self, address, handler_cls):
            self.server_address = address
            self.handler_cls = handler_cls

    monkeypatch.setattr(
        "social_research_probe.commands.serve_report.ThreadingHTTPServer", _FakeHttpServer
    )
    server = serve_report_cmd._build_server(
        report, "127.0.0.1", 8123, "http://voicebox.local:17493"
    )
    assert server.server_address == ("127.0.0.1", 8123)
    assert server.handler_cls.__name__ == "_Handler"


def test_run_rejects_missing_report(tmp_path):
    with pytest.raises(ValidationError, match="report file not found"):
        serve_report_cmd.run(str(tmp_path / "missing.html"))


def test_run_wraps_server_start_errors(tmp_path, monkeypatch):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")

    def boom(report_path, host, port, voicebox_base):
        raise OSError("port busy")

    monkeypatch.setattr("social_research_probe.commands.serve_report._build_server", boom)
    with pytest.raises(ValidationError, match="cannot start report server"):
        serve_report_cmd.run(str(report), port=9000)


def test_run_closes_server_on_keyboard_interrupt(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")
    events: list[str] = []

    class _FakeServer:
        server_address = ("127.0.0.1", 8123)

        def serve_forever(self) -> None:
            events.append("serve")
            raise KeyboardInterrupt

        def server_close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "social_research_probe.commands.serve_report._build_server",
        lambda report_path, host, port, voicebox_base: _FakeServer(),
    )
    assert serve_report_cmd.run(str(report)) == 0
    assert events == ["serve", "close"]
    assert "http://127.0.0.1:8123/" in capsys.readouterr().out


def test_run_returns_zero_when_server_exits_cleanly(tmp_path, monkeypatch):
    report = tmp_path / "report.html"
    report.write_text("<html></html>", encoding="utf-8")
    events: list[str] = []

    class _FakeServer:
        server_address = ("127.0.0.1", 8124)

        def serve_forever(self) -> None:
            events.append("serve")

        def server_close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "social_research_probe.commands.serve_report._build_server",
        lambda report_path, host, port, voicebox_base: _FakeServer(),
    )
    assert serve_report_cmd.run(str(report)) == 0
    assert events == ["serve", "close"]


class TestServeReportCoverageGaps:
    def test_handler_log_message_does_nothing(self, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")
        handler_cls = serve_report_cmd._make_handler(report, "http://voicebox.local:17493")
        handler = object.__new__(handler_cls)
        # Should return without doing anything
        assert handler.log_message("test") is None

    def test_resolve_local_file_empty_relative(self, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")
        handler_cls = serve_report_cmd._make_handler(report, "http://voicebox.local:17493")
        status, _, body = _invoke_handler(handler_cls, method="GET", path="//")
        assert status == 404
        assert b"Not Found" in body

    def test_guess_content_type_mp3(self, tmp_path):
        mp3 = tmp_path / "clip.mp3"
        assert serve_report_cmd._guess_content_type(mp3) == "audio/mpeg"
