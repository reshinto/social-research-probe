"""Tests for simple command modules."""

from __future__ import annotations

import argparse
import importlib
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.commands as _commands
from social_research_probe.utils.core.errors import ValidationError

# Capture the function references *before* importing the submodules,
# because `import a.b` binds the submodule to `a.b` and overwrites any
# function of the same name that lives in `a/__init__.py`.
_FN_SHOW_TOPICS = _commands.list_topics
_FN_SHOW_PURPOSES = _commands.list_purposes
_FN_STAGE_SUGGESTIONS = _commands.add_pending_suggestions
_FN_LOAD_PENDING = _commands.load_pending
_FN_ADD_TOPICS = _commands.add_topics
_FN_ADD_PURPOSE = _commands.add_purpose


def _load_cmd(name):
    """Import a command submodule and restore any clobbered function attribute."""
    saved = {
        "show_topics": _FN_SHOW_TOPICS,
        "show_purposes": _FN_SHOW_PURPOSES,
        "stage_suggestions": _FN_STAGE_SUGGESTIONS,
    }
    module = importlib.import_module(f"social_research_probe.commands.{name}")
    for attr, fn in saved.items():
        if attr != name:
            setattr(_commands, attr, fn)
    return module


update_topics = _load_cmd("update_topics")
update_purposes = _load_cmd("update_purposes")
discard_pending = _load_cmd("discard_pending")
apply_pending = _load_cmd("apply_pending")
show_pending = _load_cmd("show_pending")
show_topics_mod = _load_cmd("show_topics")
show_purposes_mod = _load_cmd("show_purposes")
stage_suggestions_mod = _load_cmd("stage_suggestions")


@pytest.fixture(autouse=True)
def _restore_command_functions():
    """Re-pin the function attributes before each test (submodule imports clobber them)."""
    _commands.show_topics = _FN_SHOW_TOPICS
    _commands.show_purposes = _FN_SHOW_PURPOSES
    _commands.stage_suggestions = _FN_STAGE_SUGGESTIONS
    yield


@pytest.fixture
def isolated(tmp_path: Path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


class TestShowTopics:
    def test_run_empty(self, isolated, capsys):
        rc = show_topics_mod.run(argparse.Namespace(output="json"))
        assert rc == 0
        assert json.loads(capsys.readouterr().out) == {"topics": []}


class TestShowPurposes:
    def test_run_empty(self, isolated, capsys):
        rc = show_purposes_mod.run(argparse.Namespace(output="json"))
        assert rc == 0
        assert json.loads(capsys.readouterr().out) == {"purposes": {}}


class TestShowPending:
    def test_run(self, isolated, capsys):
        rc = show_pending.run(argparse.Namespace(output="json"))
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["pending_topic_suggestions"] == []


class TestUpdateTopics:
    def test_add(self, isolated, capsys):
        ns = argparse.Namespace(
            add=["a", "b"], remove=None, rename=None, force=False, output="json"
        )
        assert update_topics.run(ns) == 0
        assert "a" in _FN_SHOW_TOPICS()

    def test_remove(self, isolated, capsys):
        _FN_ADD_TOPICS(["a"], force=False)
        ns = argparse.Namespace(add=None, remove=["a"], rename=None, force=False, output="json")
        assert update_topics.run(ns) == 0
        assert "a" not in _FN_SHOW_TOPICS()

    def test_rename(self, isolated, capsys):
        _FN_ADD_TOPICS(["old"], force=False)
        ns = argparse.Namespace(
            add=None, remove=None, rename=("old", "new"), force=False, output="json"
        )
        assert update_topics.run(ns) == 0


class TestUpdatePurposes:
    def test_add(self, isolated, capsys):
        ns = argparse.Namespace(
            add=["career", "learn"], remove=None, rename=None, force=False, output="json"
        )
        assert update_purposes.run(ns) == 0
        assert "career" in _FN_SHOW_PURPOSES()

    def test_add_wrong_arity(self, isolated):
        ns = argparse.Namespace(add=["only"], remove=None, rename=None, force=False, output="json")
        with pytest.raises(ValidationError):
            update_purposes.run(ns)

    def test_remove(self, isolated, capsys):
        _FN_ADD_PURPOSE(name="x", method="m", force=False)
        ns = argparse.Namespace(add=None, remove=["x"], rename=None, force=False, output="json")
        assert update_purposes.run(ns) == 0

    def test_rename(self, isolated, capsys):
        _FN_ADD_PURPOSE(name="old", method="m", force=False)
        ns = argparse.Namespace(
            add=None, remove=None, rename=("old", "new"), force=False, output="json"
        )
        assert update_purposes.run(ns) == 0


class TestDiscardPending:
    def test_run_all(self, isolated, capsys):
        _FN_STAGE_SUGGESTIONS(topic_candidates=[{"value": "x"}], purpose_candidates=[])
        ns = argparse.Namespace(topics="all", purposes="", output="json")
        assert discard_pending.run(ns) == 0
        assert _FN_LOAD_PENDING()["pending_topic_suggestions"] == []


class TestApplyPending:
    def test_run_all(self, isolated, capsys):
        _FN_STAGE_SUGGESTIONS(
            topic_candidates=[{"value": "x"}],
            purpose_candidates=[{"name": "p", "method": "M"}],
        )
        ns = argparse.Namespace(topics="all", purposes="all", output="json")
        rc = apply_pending.run(ns)
        assert rc == 0
        assert "x" in _FN_SHOW_TOPICS()
        assert "p" in _FN_SHOW_PURPOSES()


class TestStageSuggestions:
    def test_requires_stdin(self, isolated):
        ns = argparse.Namespace(from_stdin=False, output="json")
        with pytest.raises(ValidationError):
            stage_suggestions_mod.run(ns)

    def test_invalid_json_raises(self, isolated, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        ns = argparse.Namespace(from_stdin=True, output="json")
        with pytest.raises(ValidationError):
            stage_suggestions_mod.run(ns)

    def test_basic(self, isolated, monkeypatch, capsys):
        payload = json.dumps({"topic_candidates": [{"value": "x"}], "purpose_candidates": []})
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        ns = argparse.Namespace(from_stdin=True, output="json")
        assert stage_suggestions_mod.run(ns) == 0
