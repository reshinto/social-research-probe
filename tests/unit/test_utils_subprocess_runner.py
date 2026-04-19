"""
Tests for ``social_research_probe.utils.subprocess_runner``.

Verifies that ``run`` returns a ``CompletedProcess`` on success, raises
``AdapterError`` when the exit code is non-zero, raises ``AdapterError`` when
the subprocess times out, and includes the subprocess stderr in the error
message for failed commands.
"""

from __future__ import annotations

import subprocess

import pytest

from social_research_probe.errors import AdapterError
from social_research_probe.utils.subprocess_runner import run


def test_run_success() -> None:
    """A zero-exit-code command must return a CompletedProcess with correct stdout."""
    result = run(["echo", "hello"])
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.stdout == "hello\n"
    assert result.returncode == 0


def test_run_nonzero_raises_adapter_error() -> None:
    """A non-zero exit code must raise AdapterError."""
    with pytest.raises(AdapterError):
        run(["false"])


def test_run_timeout_raises_adapter_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A TimeoutExpired from subprocess.run must be re-raised as AdapterError."""

    def _fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["sleep", "99"], timeout=1)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.subprocess.run", _fake_run)

    with pytest.raises(AdapterError, match="timed out"):
        run(["sleep", "99"], timeout=1)


def test_run_stderr_in_message() -> None:
    """The AdapterError message for a failed command must contain the stderr output."""
    # Use a shell command that writes a known string to stderr and exits non-zero.
    with pytest.raises(AdapterError, match="No such file or directory") as exc_info:
        run(["ls", "/this/path/does/not/exist/srp_test"])

    # Double-check the message carries the stderr fragment.
    assert "No such file or directory" in str(exc_info.value)
