"""Tests for Phase 3 export-related types and config defaults."""

from __future__ import annotations

import json

from social_research_probe.utils.core.types import (
    ExportConfig,
    ResearchReport,
    YouTubePlatformConfig,
)


def test_export_config_all_fields():
    cfg: ExportConfig = {
        "enabled": True,
        "sources_csv": True,
        "comments_csv": True,
        "methodology_md": True,
        "run_summary_json": True,
    }
    assert cfg["enabled"] is True
    assert cfg["sources_csv"] is True
    assert cfg["run_summary_json"] is True


def test_export_config_json_serializable():
    cfg: ExportConfig = {
        "enabled": True,
        "sources_csv": False,
        "comments_csv": True,
        "methodology_md": True,
        "run_summary_json": False,
    }
    serialized = json.dumps(cfg)
    roundtrip = json.loads(serialized)
    assert roundtrip["enabled"] is True
    assert roundtrip["sources_csv"] is False


def test_platform_config_accepts_export():
    plat: YouTubePlatformConfig = {
        "recency_days": 90,
        "max_items": 20,
        "enrich_top_n": 5,
        "export": {
            "enabled": True,
            "sources_csv": True,
            "comments_csv": True,
            "methodology_md": True,
            "run_summary_json": True,
        },
    }
    assert plat["export"]["enabled"] is True


def test_report_accepts_export_paths():
    report: ResearchReport = {
        "topic": "AI safety",
        "export_paths": {
            "sources_csv": "/tmp/sources.csv",
            "comments_csv": "/tmp/comments.csv",
        },
    }
    assert report["export_paths"]["sources_csv"] == "/tmp/sources.csv"


def test_default_config_has_export_platform():
    from social_research_probe.config import DEFAULT_CONFIG

    export = DEFAULT_CONFIG["platforms"]["youtube"]["export"]
    assert export["enabled"] is True
    assert export["sources_csv"] is True
    assert export["comments_csv"] is True
    assert export["methodology_md"] is True
    assert export["run_summary_json"] is True


def test_default_config_has_export_stage():
    from social_research_probe.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["stages"]["youtube"]["export"] is True


def test_default_config_has_export_service():
    from social_research_probe.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["services"]["youtube"]["reporting"]["export"] is True


def test_default_config_has_export_tech():
    from social_research_probe.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["technologies"]["export_package"] is True


def test_stage_enabled_export(tmp_path):
    from social_research_probe.config import Config

    cfg = Config(
        data_dir=tmp_path,
        raw={
            "stages": {"youtube": {"export": True}},
            "services": {},
            "technologies": {},
        },
    )
    assert cfg.stage_enabled("youtube", "export") is True


def test_technology_enabled_export_package(tmp_path):
    from social_research_probe.config import Config

    cfg = Config(
        data_dir=tmp_path,
        raw={
            "stages": {},
            "services": {},
            "technologies": {"export_package": True},
        },
    )
    assert cfg.technology_enabled("export_package") is True
