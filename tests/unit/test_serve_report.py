"""Tests for commands.serve_report."""

from __future__ import annotations

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import serve_report
from social_research_probe.utils.core.errors import ValidationError


def test_default_voicebox_base():
    cfg = MagicMock()
    cfg.voicebox = {"api_base": "http://x"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert serve_report._default_voicebox_base() == "http://x"


def test_rewrite_html():
    out = serve_report._rewrite_report_html('<div data-api-base="http://orig"></div>')
    assert "/voicebox/" in out
    assert "http://orig" not in out


def test_proxy_timeout_seconds():
    assert (
        serve_report._proxy_timeout_seconds("/voicebox/generate/stream")
        == serve_report._STREAM_PROXY_TIMEOUT_SECONDS
    )
    assert serve_report._proxy_timeout_seconds("/x") == serve_report._DEFAULT_PROXY_TIMEOUT_SECONDS


def test_resolve_safe_local_file_empty(tmp_path):
    assert serve_report._resolve_safe_local_file("/", tmp_path) is None


def test_resolve_safe_local_file_traversal(tmp_path):
    assert serve_report._resolve_safe_local_file("/../../../etc/passwd", tmp_path) is None


def test_resolve_safe_local_file_directory(tmp_path):
    sub = tmp_path / "x"
    sub.mkdir()
    assert serve_report._resolve_safe_local_file("/x", tmp_path) is None


def test_resolve_safe_local_file_match(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("y")
    assert serve_report._resolve_safe_local_file("/x.txt", tmp_path) == f


def test_guess_content_type():
    assert serve_report._guess_content_type(Path("a.wav")) == "audio/wav"
    assert serve_report._guess_content_type(Path("a.mp3")) == "audio/mpeg"
    assert serve_report._guess_content_type(Path("a.html")).startswith("text/html")
    assert serve_report._guess_content_type(Path("a.unknown")) == "application/octet-stream"


def test_resolve_report_file_missing():
    with pytest.raises(ValidationError):
        serve_report._resolve_report_file("/nope/x.html")


def test_resolve_report_file_ok(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<html/>")
    assert serve_report._resolve_report_file(str(f)) == f.resolve()


def test_get_proxy_target_arg():
    assert serve_report._get_proxy_target("http://from-arg") == "http://from-arg"


def test_get_proxy_target_env(monkeypatch):
    monkeypatch.setenv("SRP_VOICEBOX_API_BASE", "http://from-env")
    assert serve_report._get_proxy_target(None) == "http://from-env"


def test_get_proxy_target_config(monkeypatch):
    monkeypatch.delenv("SRP_VOICEBOX_API_BASE", raising=False)
    cfg = MagicMock()
    cfg.voicebox = {"api_base": "http://cfg"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert serve_report._get_proxy_target(None) == "http://cfg"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_build_server(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.commands.serve_report.ThreadingHTTPServer", MagicMock()
    )
    f = tmp_path / "x.html"
    server = serve_report._build_server(f, "127.0.0.1", 8000, "http://x")
    assert server is not None


def test_make_handler_serves_html(tmp_path):
    f = tmp_path / "r.html"
    f.write_text('<div data-api-base="http://orig"></div>')

    handler_class = serve_report._make_handler(f, "http://nope")
    handler = handler_class.__new__(handler_class)
    handler.path = "/"
    handler.wfile = MagicMock()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.wfile.write.assert_called()
    written = b"".join(call.args[0] for call in handler.wfile.write.mock_calls).decode()
    assert "/voicebox/" in written

    handler.path = "/r.html"
    handler.wfile.write.reset_mock()
    handler.do_GET()
    handler.send_response.assert_called_with(200)

    handler.path = "/missing"
    handler.send_error = MagicMock()
    handler.do_GET()
    handler.send_error.assert_called_with(404, "Not Found")


def test_run_oserror(tmp_path, monkeypatch):
    f = tmp_path / "r.html"
    f.write_text("<x/>")

    def boom(*a, **kw):
        raise OSError("addr in use")

    monkeypatch.setattr(serve_report, "_build_server", boom)
    monkeypatch.delenv("SRP_VOICEBOX_API_BASE", raising=False)
    cfg = MagicMock()
    cfg.voicebox = {"api_base": "http://x"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError):
            serve_report.run(str(f))


def test_run_success(tmp_path, monkeypatch, capsys):
    f = tmp_path / "r.html"
    f.write_text("<x/>")

    server = MagicMock()
    server.server_address = ("127.0.0.1", 5)
    server.serve_forever.side_effect = KeyboardInterrupt

    monkeypatch.setattr(serve_report, "_build_server", lambda *a, **kw: server)
    monkeypatch.delenv("SRP_VOICEBOX_API_BASE", raising=False)
    cfg = MagicMock()
    cfg.voicebox = {"api_base": "http://x"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        rc = serve_report.run(str(f))
    assert rc == 0
    server.server_close.assert_called_once()
