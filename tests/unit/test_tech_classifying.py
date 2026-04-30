"""Tests for tech.classifying (heuristic, llm, hybrid)."""

from __future__ import annotations

import pytest

from social_research_probe.technologies import classifying as cls_mod
from social_research_probe.technologies.classifying import (
    HeuristicClassifier,
    HybridClassifier,
    LLMClassifier,
    classify_by_channel_name_signal,
    classify_by_curated_map,
    classify_by_title_signal,
    coerce_class,
)


class TestCuratedMap:
    def test_primary_match(self):
        assert classify_by_curated_map("BBC News") == "primary"
        assert classify_by_curated_map("Reuters") == "primary"

    def test_secondary_match(self):
        assert classify_by_curated_map("Vox") == "secondary"

    def test_commentary_match(self):
        assert classify_by_curated_map("Daily Tech Podcast") == "commentary"

    def test_unknown_when_no_match(self):
        assert classify_by_curated_map("Random Channel 12345") == "unknown"

    def test_empty_channel(self):
        assert classify_by_curated_map("") == "unknown"

    def test_case_insensitive(self):
        assert classify_by_curated_map("REUTERS") == "primary"


class TestTitleSignal:
    def test_reaction(self):
        assert classify_by_title_signal("My reaction to the news") == "commentary"

    def test_reacts(self):
        assert classify_by_title_signal("CEO reacts to layoffs") == "commentary"

    def test_opinion(self):
        assert classify_by_title_signal("Opinion: why this matters") == "commentary"

    def test_no_signal(self):
        assert classify_by_title_signal("Quarterly earnings results") == "unknown"

    def test_empty_title(self):
        assert classify_by_title_signal("") == "unknown"


class TestChannelNameSignal:
    def test_news_token(self):
        assert classify_by_channel_name_signal("Local News Network") == "primary"

    def test_official_token(self):
        assert classify_by_channel_name_signal("Tesla Official") == "primary"

    def test_no_signal(self):
        assert classify_by_channel_name_signal("Random Channel") == "unknown"

    def test_empty(self):
        assert classify_by_channel_name_signal("") == "unknown"


class TestCoerceClass:
    def test_valid(self):
        assert coerce_class("primary") == "primary"
        assert coerce_class("Commentary") == "commentary"

    def test_invalid_value(self):
        assert coerce_class("nonsense") == "unknown"

    def test_non_string(self):
        assert coerce_class(None) == "unknown"
        assert coerce_class(42) == "unknown"


class TestHeuristicClassifier:
    @pytest.mark.asyncio
    async def test_curated_hit(self):
        out = await HeuristicClassifier()._execute({"channel": "BBC News", "title": ""})
        assert out == "primary"

    @pytest.mark.asyncio
    async def test_falls_through_to_name_signal(self):
        out = await HeuristicClassifier()._execute({"channel": "Riverside News", "title": ""})
        assert out == "primary"

    @pytest.mark.asyncio
    async def test_falls_through_to_title_signal(self):
        out = await HeuristicClassifier()._execute(
            {"channel": "Random Indie", "title": "My reaction video"}
        )
        assert out == "commentary"

    @pytest.mark.asyncio
    async def test_unknown_when_nothing_matches(self):
        out = await HeuristicClassifier()._execute(
            {"channel": "Indie Studio", "title": "Behind the scenes"}
        )
        assert out == "unknown"

    @pytest.mark.asyncio
    async def test_uses_author_name_when_no_channel(self):
        out = await HeuristicClassifier()._execute({"author_name": "Reuters"})
        assert out == "primary"


class TestLLMClassifier:
    @pytest.mark.asyncio
    async def test_returns_unknown_when_no_runner(self, monkeypatch):
        from social_research_probe import config as cfg_mod

        class FakeCfg:
            preferred_free_text_runner = None

            def debug_enabled(self, _: str) -> bool:
                return False

        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "unknown"

    @pytest.mark.asyncio
    async def test_returns_runner_payload(self, monkeypatch):
        from social_research_probe import config as cfg_mod
        from social_research_probe.utils.llm import registry

        class FakeCfg:
            preferred_free_text_runner = "claude"

            def debug_enabled(self, _: str) -> bool:
                return False

        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(
            registry, "run_with_fallback", lambda p, schema, preferred: {"source_class": "primary"}
        )
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "primary"

    @pytest.mark.asyncio
    async def test_returns_unknown_when_runner_raises(self, monkeypatch):
        from social_research_probe import config as cfg_mod
        from social_research_probe.utils.llm import registry

        class FakeCfg:
            preferred_free_text_runner = "claude"

            def debug_enabled(self, _: str) -> bool:
                return False

        def boom(*a, **kw):
            raise RuntimeError("nope")

        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(registry, "run_with_fallback", boom)
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "unknown"

    @pytest.mark.asyncio
    async def test_returns_unknown_for_non_dict_payload(self, monkeypatch):
        from social_research_probe import config as cfg_mod
        from social_research_probe.utils.llm import registry

        class FakeCfg:
            preferred_free_text_runner = "claude"

            def debug_enabled(self, _: str) -> bool:
                return False

        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(
            registry, "run_with_fallback", lambda p, schema, preferred: "not-a-dict"
        )
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "unknown"


class TestChannelNameSignalExtended:
    def test_secondary_pattern_tech(self):
        assert classify_by_channel_name_signal("AI Tech Daily") == "secondary"

    def test_secondary_pattern_review(self):
        assert classify_by_channel_name_signal("Gadget Reviews") == "secondary"

    def test_commentary_pattern_podcast(self):
        assert classify_by_channel_name_signal("The AI Podcast") == "commentary"

    def test_commentary_pattern_show(self):
        assert classify_by_channel_name_signal("Morning Show") == "commentary"

    def test_primary_pattern_reporting(self):
        assert classify_by_channel_name_signal("Daily Reporting") == "primary"


class TestLLMClassifierDebugLogging:
    @pytest.mark.asyncio
    async def test_debug_log_no_runner(self, monkeypatch):
        from social_research_probe import config as cfg_mod

        class FakeCfg:
            preferred_free_text_runner = None

            def debug_enabled(self, _: str) -> bool:
                return True

        logged: list[str] = []
        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(
            "social_research_probe.utils.display.progress.log",
            lambda msg: logged.append(msg),
        )
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "unknown"
        assert any("no runner configured" in m for m in logged)

    @pytest.mark.asyncio
    async def test_debug_log_runner_failure(self, monkeypatch):
        from social_research_probe import config as cfg_mod
        from social_research_probe.utils.llm import registry

        class FakeCfg:
            preferred_free_text_runner = "claude"

            def debug_enabled(self, _: str) -> bool:
                return True

        logged: list[str] = []
        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(
            registry,
            "run_with_fallback",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.progress.log",
            lambda msg: logged.append(msg),
        )
        out = await LLMClassifier()._execute({"channel": "X", "title": "Y"})
        assert out == "unknown"
        assert any("runner failed" in m for m in logged)

    @pytest.mark.asyncio
    async def test_debug_log_success(self, monkeypatch):
        from social_research_probe import config as cfg_mod
        from social_research_probe.utils.llm import registry

        class FakeCfg:
            preferred_free_text_runner = "claude"

            def debug_enabled(self, _: str) -> bool:
                return True

        logged: list[str] = []
        monkeypatch.setattr(cfg_mod, "load_active_config", lambda: FakeCfg())
        monkeypatch.setattr(
            registry,
            "run_with_fallback",
            lambda p, schema, preferred: {"source_class": "secondary"},
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.progress.log",
            lambda msg: logged.append(msg),
        )
        out = await LLMClassifier()._execute({"channel": "TechGuru", "title": "AI"})
        assert out == "secondary"
        assert any("TechGuru" in m and "secondary" in m for m in logged)


class TestHybridClassifier:
    @pytest.mark.asyncio
    async def test_uses_heuristic_when_match(self, monkeypatch):
        # Heuristic finds a curated entry, so LLM must not be called
        async def fail(*a, **kw):
            raise AssertionError("LLM should not be called")

        monkeypatch.setattr(cls_mod.LLMClassifier, "_execute", fail)
        out = await HybridClassifier()._execute({"channel": "BBC News", "title": ""})
        assert out == "primary"

    @pytest.mark.asyncio
    async def test_falls_back_to_llm_when_heuristic_unknown(self, monkeypatch):
        async def fake_llm(self, data):
            return "secondary"

        monkeypatch.setattr(cls_mod.LLMClassifier, "_execute", fake_llm)
        out = await HybridClassifier()._execute(
            {"channel": "Totally Unknown Indie", "title": "behind the scenes"}
        )
        assert out == "secondary"
