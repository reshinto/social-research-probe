"""Tests for commands.research."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import research
from social_research_probe.utils.core.errors import ValidationError


class TestParseInput:
    def test_empty(self):
        with pytest.raises(ValidationError):
            research._parse_research_input([])

    def test_platform_only(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        with pytest.raises(ValidationError):
            research._parse_research_input(["youtube"])

    def test_query(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        out = research._parse_research_input(["youtube", "what is x"])
        assert out.query == "what is x"
        assert out.topic == ""

    def test_topic_purposes(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        out = research._parse_research_input(["youtube", "ai", "career,growth"])
        assert out.topic == "ai"
        assert out.purposes == ("career", "growth")

    def test_too_many(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        with pytest.raises(ValidationError):
            research._parse_research_input(["youtube", "a", "b", "c"])

    def test_no_purposes(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        with pytest.raises(ValidationError):
            research._parse_research_input(["youtube", "ai", ","])

    def test_default_platform_all(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.PIPELINES",
            {"youtube": object, "all": object},
        )
        out = research._parse_research_input(["topic", "purpose"])
        assert out.platform == "all"


def test_normalize_with_query(monkeypatch):
    monkeypatch.setattr(research, "_classify_query_to_topic_purposes", lambda q: ("t", ("p",)))
    args = research._ResearchArgs(platform="x", topic="", purposes=(), query="qq")
    out = research._normalize_to_topic_and_purposes(args)
    assert out == ("t", ("p",))


def test_normalize_without_query():
    args = research._ResearchArgs(platform="x", topic="t", purposes=("p",), query="")
    assert research._normalize_to_topic_and_purposes(args) == ("t", ("p",))


def test_classify_query_delegates(monkeypatch):
    fake = MagicMock(topic="T", purpose_name="P")
    with patch(
        "social_research_probe.services.llm.classify_query.classify_query",
        return_value=fake,
    ):
        out = research._classify_query_to_topic_purposes("q")
    assert out == ("T", ("P",))


def test_apply_cli_overrides(monkeypatch):
    cfg = MagicMock()
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        ns = argparse.Namespace(no_shorts=True, no_transcripts=False, no_html=True)
        research._apply_cli_overrides(ns)
    cfg.apply_platform_overrides.assert_called_once()


def test_run_basic(monkeypatch, capsys):
    monkeypatch.setattr(
        "social_research_probe.platforms.PIPELINES",
        {"youtube": object, "all": object},
    )
    monkeypatch.setattr(research, "_apply_cli_overrides", lambda a: None)
    monkeypatch.setattr(
        research, "_execute_research_pipeline", lambda p, t, ps: {"report_path": "/x"}
    )
    ns = argparse.Namespace(args=["youtube", "ai", "career"])
    rc = research.run(ns)
    assert rc == 0
    assert "/x" in capsys.readouterr().out
