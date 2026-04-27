"""Tests for utils.secrets."""

from __future__ import annotations

from unittest.mock import patch

from social_research_probe.utils import secrets


def test_user_agent_includes_package():
    assert "social-research-probe/" in secrets.HTTP_USER_AGENT


def test_read_runtime_secret_delegates(monkeypatch):
    with patch.object(secrets, "read_secret", return_value="VAL") as mock_read:
        assert secrets.read_runtime_secret("API_KEY") == "VAL"
    mock_read.assert_called_once_with("API_KEY")


def test_read_runtime_secret_none(monkeypatch):
    with patch.object(secrets, "read_secret", return_value=None):
        assert secrets.read_runtime_secret("MISSING") is None
