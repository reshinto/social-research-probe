"""Tests for utils.io.io and utils.io.subprocess_runner."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.io.io import _srp_json_default, read_json, write_json
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

    def test_writes_list(self, tmp_path: Path):
        path = tmp_path / "list.json"
        write_json(path, [1, 2, 3])
        assert json.loads(path.read_text()) == [1, 2, 3]

    def test_writes_string(self, tmp_path: Path):
        path = tmp_path / "str.json"
        write_json(path, "hello")
        assert json.loads(path.read_text()) == "hello"

    def test_writes_dataclass(self, tmp_path: Path):
        @dataclasses.dataclass
        class Point:
            x: int
            y: int

        path = tmp_path / "dc.json"
        write_json(path, Point(x=1, y=2))
        assert json.loads(path.read_text()) == {"x": 1, "y": 2}

    def test_writes_path(self, tmp_path: Path):
        path = tmp_path / "p.json"
        write_json(path, {"p": Path("/some/path")})
        assert json.loads(path.read_text()) == {"p": "/some/path"}

    def test_writes_datetime(self, tmp_path: Path):
        dt = datetime(2024, 1, 15, 12, 0, 0)
        path = tmp_path / "dt.json"
        write_json(path, {"ts": dt})
        result = json.loads(path.read_text())
        assert "2024-01-15" in result["ts"]

    def test_permission_error_cleans_tmp(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        with patch("os.replace", side_effect=PermissionError("denied")):
            with pytest.raises(PermissionError):
                write_json(path, {"k": "v"})
        assert not (tmp_path / "bad.tmp").exists()


class TestSrpJsonDefault:
    def test_dataclass_converted_to_dict(self):
        @dataclasses.dataclass
        class Item:
            name: str
            count: int

        result = _srp_json_default(Item(name="foo", count=3))
        assert result == {"name": "foo", "count": 3}

    def test_path_converted_to_str(self):
        assert _srp_json_default(Path("/tmp/x")) == "/tmp/x"

    def test_datetime_converted_to_str(self):
        dt = datetime(2024, 6, 1)
        result = _srp_json_default(dt)
        assert "2024-06-01" in result

    def test_unknown_type_falls_back_to_repr(self):
        class Weird:
            def __repr__(self):
                return "weird-repr"

        result = _srp_json_default(Weird())
        assert result == "weird-repr"


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
