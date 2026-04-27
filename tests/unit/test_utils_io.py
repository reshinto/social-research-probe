"""Tests for utils.io.io and utils.io.subprocess_runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.io.io import read_json, write_json
from social_research_probe.utils.io.subprocess_runner import run


class TestReadJson:
    def test_missing_returns_default_copy(self, tmp_path: Path):
        default = {"x": 1}
        result = read_json(tmp_path / "missing.json", default=default)
        assert result == {"x": 1}
        result["y"] = 2
        assert default == {"x": 1}

    def test_missing_with_no_default_returns_empty(self, tmp_path: Path):
        assert read_json(tmp_path / "absent.json") == {}

    def test_reads_existing_file(self, tmp_path: Path):
        path = tmp_path / "data.json"
        path.write_text('{"a": 1, "b": [2, 3]}')
        assert read_json(path) == {"a": 1, "b": [2, 3]}

    def test_invalid_json_raises(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            read_json(path)


class TestWriteJson:
    def test_creates_file_and_parents(self, tmp_path: Path):
        path = tmp_path / "nested" / "dir" / "out.json"
        write_json(path, {"k": "v"})
        assert json.loads(path.read_text()) == {"k": "v"}

    def test_overwrites_existing(self, tmp_path: Path):
        path = tmp_path / "out.json"
        path.write_text('{"old": true}')
        write_json(path, {"new": True})
        assert json.loads(path.read_text()) == {"new": True}

    def test_unserializable_raises_and_cleans_tmp(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        with pytest.raises(TypeError):
            write_json(path, {"k": object()})
        assert not (tmp_path / "bad.tmp").exists()


class TestSubprocessRun:
    def test_success(self):
        result = run(["true"])
        assert result.returncode == 0

    def test_nonzero_raises(self):
        with pytest.raises(AdapterError, match="failed"):
            run(["false"])

    def test_captures_stdout(self):
        result = run(["echo", "hello"])
        assert "hello" in result.stdout

    def test_timeout_raises_adapter_error(self):
        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        with patch("subprocess.run", side_effect=raise_timeout):
            with pytest.raises(AdapterError, match="timed out"):
                run(["sleep", "10"], timeout=1)

    def test_input_passed(self):
        result = run(["cat"], input="hello world")
        assert "hello world" in result.stdout
