"""Tests for commands/__init__ topic and purpose helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe import commands
from social_research_probe.utils.core.errors import DuplicateError, ValidationError


@pytest.fixture
def isolated_data_dir(tmp_path: Path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


class TestTopics:
    def test_show_empty(self, isolated_data_dir):
        assert commands.list_topics() == []

    def test_add_one(self, isolated_data_dir):
        commands.add_topics(["AI agents"], force=False)
        assert "AI agents" in commands.list_topics()

    def test_add_duplicate_raises(self, isolated_data_dir):
        commands.add_topics(["AI"], force=False)
        with pytest.raises(DuplicateError):
            commands.add_topics(["ai"], force=False)

    def test_add_force_dupe(self, isolated_data_dir):
        commands.add_topics(["AI"], force=False)
        commands.add_topics(["AI"], force=True)

    def test_remove(self, isolated_data_dir):
        commands.add_topics(["x", "y"], force=False)
        commands.remove_topics(["x"])
        assert "x" not in commands.list_topics()

    def test_remove_missing_raises(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.remove_topics(["nope"])

    def test_rename(self, isolated_data_dir):
        commands.add_topics(["old"], force=False)
        commands.rename_topic("old", "new")
        assert "new" in commands.list_topics()

    def test_rename_missing(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.rename_topic("missing", "x")

    def test_rename_to_existing(self, isolated_data_dir):
        commands.add_topics(["a", "b"], force=False)
        with pytest.raises(ValidationError):
            commands.rename_topic("a", "b")


class TestPurposes:
    def test_show_empty(self, isolated_data_dir):
        assert commands.list_purposes() == {}

    def test_add(self, isolated_data_dir):
        commands.add_purpose(name="career", method="learn", force=False)
        assert "career" in commands.list_purposes()

    def test_empty_method_raises(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.add_purpose(name="x", method="   ", force=False)

    def test_add_duplicate(self, isolated_data_dir):
        commands.add_purpose(name="career", method="m", force=False)
        with pytest.raises(DuplicateError):
            commands.add_purpose(name="career", method="m2", force=False)

    def test_remove(self, isolated_data_dir):
        commands.add_purpose(name="x", method="m", force=False)
        commands.remove_purposes(["x"])
        assert "x" not in commands.list_purposes()

    def test_remove_missing(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.remove_purposes(["nope"])

    def test_rename(self, isolated_data_dir):
        commands.add_purpose(name="old", method="m", force=False)
        commands.rename_purpose("old", "new")
        assert "new" in commands.list_purposes()

    def test_rename_missing(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.rename_purpose("missing", "x")

    def test_rename_to_existing(self, isolated_data_dir):
        commands.add_purpose(name="a", method="m", force=False)
        commands.add_purpose(name="b", method="m2", force=False)
        with pytest.raises(ValidationError):
            commands.rename_purpose("a", "b")


class TestPending:
    def test_load_default(self, isolated_data_dir):
        pending = commands.load_pending()
        assert pending["pending_topic_suggestions"] == []
        assert pending["pending_purpose_suggestions"] == []

    def test_select_all(self):
        entries = [{"id": 1}, {"id": 2}]
        chosen, remaining = commands.select_pending(entries, "all")
        assert chosen == entries
        assert remaining == []

    def test_select_by_ids(self):
        entries = [{"id": 1}, {"id": 2}, {"id": 3}]
        chosen, remaining = commands.select_pending(entries, [1, 3])
        assert [e["id"] for e in chosen] == [1, 3]
        assert [e["id"] for e in remaining] == [2]

    def test_stage_topic_suggestion(self, isolated_data_dir):
        out = commands.add_pending_suggestions(
            topic_candidates=[{"value": "ai"}], purpose_candidates=[]
        )
        assert out["pending_topic_suggestions"][0]["value"] == "ai"

    def test_stage_topic_missing_value(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.add_pending_suggestions(topic_candidates=[{}], purpose_candidates=[])

    def test_stage_purpose_missing_keys(self, isolated_data_dir):
        with pytest.raises(ValidationError):
            commands.add_pending_suggestions(
                topic_candidates=[], purpose_candidates=[{"name": "x"}]
            )

    def test_stage_purpose_full(self, isolated_data_dir):
        out = commands.add_pending_suggestions(
            topic_candidates=[],
            purpose_candidates=[{"name": "career", "method": "M", "evidence_priorities": ["x"]}],
        )
        assert out["pending_purpose_suggestions"][0]["name"] == "career"


class TestEnums:
    def test_command_values(self):
        assert commands.Command.UPDATE_TOPICS == "update-topics"
        assert commands.Command.RESEARCH == "research"

    def test_config_subcommand(self):
        assert commands.ConfigSubcommand.SHOW == "show"

    def test_special_command(self):
        assert commands.SpecialCommand.HELP == "help"
