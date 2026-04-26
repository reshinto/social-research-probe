"""Cover serve_report.py proxy paths."""

from __future__ import annotations

import urllib.error
from io import BytesIO
from unittest.mock import MagicMock

from social_research_probe.commands import serve_report


def _mk_handler(path="/voicebox/profiles", method="GET", body=b""):
    h = MagicMock()
    h.path = path
    h.command = method
    h.headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    h.rfile.read.return_value = body
    h.wfile.write = MagicMock()
    return h


def test_proxy_success(monkeypatch):
    h = _mk_handler(body=b'{"q":1}')

    class FakeResp:
        status = 200
        headers = {"Content-Type": "application/json"}

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: FakeResp())
    serve_report._proxy_voicebox_request(h, "http://x/")
    h.send_response.assert_called_with(200)


def test_proxy_http_error(monkeypatch):
    h = _mk_handler()

    class FakeHTTP(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("u", 503, "err", {"Content-Type": "text/plain"}, BytesIO(b"detail"))

        def read(self):
            return b"detail"

    monkeypatch.setattr("urllib.request.urlopen", side_effect_or_raise(FakeHTTP()))
    serve_report._proxy_voicebox_request(h, "http://x/")
    h.send_response.assert_called_with(503)


def test_proxy_url_error(monkeypatch):
    h = _mk_handler()

    def boom(*a, **kw):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    serve_report._proxy_voicebox_request(h, "http://x/")
    h.send_response.assert_called_with(serve_report._HTTP_BAD_GATEWAY)


def side_effect_or_raise(exc):
    def _inner(*a, **kw):
        raise exc

    return _inner


def test_handler_get_root(monkeypatch, tmp_path):
    f = tmp_path / "r.html"
    f.write_text('<div data-api-base="http://orig"></div>')
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/"
            self.command = "GET"
            self.headers = {}
            self.wfile = MagicMock()
            self._sent = []

        def send_response(self, code):
            self._sent.append(("response", code))

        def send_header(self, k, v):
            self._sent.append(("header", k, v))

        def end_headers(self):
            self._sent.append(("end_headers",))

    fh = FakeHandler()
    fh.do_GET()
    assert any(t[0] == "response" and t[1] == 200 for t in fh._sent)


def test_handler_get_voicebox_path(monkeypatch, tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/voicebox/profiles"
            self.command = "GET"
            self.headers = {"Content-Length": "0"}
            self.rfile = MagicMock()
            self.rfile.read.return_value = b""
            self.wfile = MagicMock()
            self.sent = []

        def send_response(self, c):
            self.sent.append(c)

        def send_header(self, k, v):
            pass

        def end_headers(self):
            pass

    monkeypatch.setattr(
        "urllib.request.urlopen",
        side_effect_or_raise(urllib.error.URLError("x")),
    )
    fh = FakeHandler()
    fh.do_GET()
    assert serve_report._HTTP_BAD_GATEWAY in fh.sent


def test_handler_get_local_file(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    asset = tmp_path / "asset.css"
    asset.write_text("body{}")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/asset.css"
            self.command = "GET"
            self.headers = {}
            self.wfile = MagicMock()
            self.sent = []

        def send_response(self, c):
            self.sent.append(c)

        def send_header(self, k, v):
            pass

        def end_headers(self):
            pass

    fh = FakeHandler()
    fh.do_GET()
    assert serve_report._HTTP_OK in fh.sent


def test_handler_get_404(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/nope"
            self.command = "GET"
            self.headers = {}
            self.wfile = MagicMock()
            self.errors = []

        def send_error(self, code, msg):
            self.errors.append((code, msg))

    fh = FakeHandler()
    fh.do_GET()
    assert fh.errors[0][0] == serve_report._HTTP_NOT_FOUND


def test_handler_post_404(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/random"
            self.command = "POST"
            self.headers = {}
            self.wfile = MagicMock()
            self.errors = []

        def send_error(self, code, msg):
            self.errors.append((code, msg))

    fh = FakeHandler()
    fh.do_POST()
    assert fh.errors[0][0] == serve_report._HTTP_NOT_FOUND


def test_handler_post_voicebox(monkeypatch, tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            self.path = "/voicebox/x"
            self.command = "POST"
            self.headers = {"Content-Length": "0"}
            self.rfile = MagicMock()
            self.rfile.read.return_value = b""
            self.wfile = MagicMock()
            self.sent = []

        def send_response(self, c):
            self.sent.append(c)

        def send_header(self, k, v):
            pass

        def end_headers(self):
            pass

    monkeypatch.setattr(
        "urllib.request.urlopen",
        side_effect_or_raise(urllib.error.URLError("x")),
    )
    fh = FakeHandler()
    fh.do_POST()
    assert serve_report._HTTP_BAD_GATEWAY in fh.sent


def test_log_message_silent(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_cls = serve_report._make_handler(f, "http://x/")

    class FakeHandler(handler_cls):
        def __init__(self):
            pass

    fh = FakeHandler()
    assert fh.log_message("ok") is None
