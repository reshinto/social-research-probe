"""Tests for Phase 3 ExportPackageTech."""

from __future__ import annotations

import asyncio
from pathlib import Path

from social_research_probe.technologies.report_render.export import ExportPackageTech


def _run(coro):
    return asyncio.run(coro)


def _make_data(tmp_path: Path, export_cfg: dict | None = None) -> dict:
    config: dict = {
        "max_items": 20,
        "enrich_top_n": 5,
        "recency_days": 90,
        "export": export_cfg
        if export_cfg is not None
        else {
            "enabled": True,
            "sources_csv": True,
            "comments_csv": True,
            "methodology_md": True,
            "run_summary_json": True,
        },
    }
    return {
        "report": {"topic": "test", "platform": "youtube", "items_top_n": []},
        "config": config,
        "stem": "test-youtube-20260502",
        "reports_dir": tmp_path,
    }


def test_tech_name():
    assert ExportPackageTech.name == "export_package"


def test_tech_enabled_config_key():
    assert ExportPackageTech.enabled_config_key == "export_package"


def test_execute_writes_all_artifacts(tmp_path: Path):
    data = _make_data(tmp_path)
    tech = ExportPackageTech()
    paths = _run(tech._execute(data))
    assert set(paths.keys()) == {
        "sources_csv",
        "comments_csv",
        "methodology_md",
        "run_summary_json",
    }
    for p in paths.values():
        assert Path(p).exists()


def test_execute_top_level_disabled_returns_empty(tmp_path: Path):
    data = _make_data(tmp_path, export_cfg={"enabled": False})
    tech = ExportPackageTech()
    paths = _run(tech._execute(data))
    assert paths == {}
    artifact_extensions = {".csv", ".md", ".json"}
    written = [f for f in tmp_path.iterdir() if f.suffix in artifact_extensions]
    assert written == []


def test_execute_respects_disabled_sources_csv(tmp_path: Path):
    cfg = {
        "enabled": True,
        "sources_csv": False,
        "comments_csv": True,
        "methodology_md": True,
        "run_summary_json": True,
    }
    data = _make_data(tmp_path, export_cfg=cfg)
    paths = _run(ExportPackageTech()._execute(data))
    assert "sources_csv" not in paths
    assert "comments_csv" in paths
    assert "methodology_md" in paths
    assert "run_summary_json" in paths


def test_execute_respects_disabled_comments_csv(tmp_path: Path):
    cfg = {
        "enabled": True,
        "sources_csv": True,
        "comments_csv": False,
        "methodology_md": True,
        "run_summary_json": True,
    }
    data = _make_data(tmp_path, export_cfg=cfg)
    paths = _run(ExportPackageTech()._execute(data))
    assert "comments_csv" not in paths
    assert len(paths) == 3


def test_execute_respects_disabled_methodology(tmp_path: Path):
    cfg = {
        "enabled": True,
        "sources_csv": True,
        "comments_csv": True,
        "methodology_md": False,
        "run_summary_json": True,
    }
    data = _make_data(tmp_path, export_cfg=cfg)
    paths = _run(ExportPackageTech()._execute(data))
    assert "methodology_md" not in paths
    assert len(paths) == 3


def test_execute_respects_disabled_run_summary(tmp_path: Path):
    cfg = {
        "enabled": True,
        "sources_csv": True,
        "comments_csv": True,
        "methodology_md": True,
        "run_summary_json": False,
    }
    data = _make_data(tmp_path, export_cfg=cfg)
    paths = _run(ExportPackageTech()._execute(data))
    assert "run_summary_json" not in paths
    assert len(paths) == 3


def test_execute_missing_optional_config(tmp_path: Path):
    data = {
        "report": {},
        "config": {},
        "stem": "fallback",
        "reports_dir": tmp_path,
    }
    tech = ExportPackageTech()
    paths = _run(tech._execute(data))
    assert set(paths.keys()) == {
        "sources_csv",
        "comments_csv",
        "methodology_md",
        "run_summary_json",
    }


def test_flat_platform_config_enabled_false_suppresses_all_artifacts(tmp_path: Path):
    """Regression: flat platform-level config shape used; full AppConfig nesting would silently ignore this flag."""
    data = {
        "report": {"topic": "test", "platform": "youtube", "items_top_n": []},
        "config": {"export": {"enabled": False}},
        "stem": "regression",
        "reports_dir": tmp_path,
    }
    paths = _run(ExportPackageTech()._execute(data))
    assert paths == {}
    artifact_extensions = {".csv", ".md", ".json"}
    written = [f for f in tmp_path.iterdir() if f.suffix in artifact_extensions]
    assert written == []


def test_run_summary_includes_html_report_when_available(tmp_path: Path):
    """Regression: run_summary.json artifact_paths includes html_report when set on report."""
    import json

    data = _make_data(tmp_path)
    html_file = tmp_path / "demo.html"
    html_file.write_text("<html></html>", encoding="utf-8")
    data["report"]["html_report_path"] = html_file.as_uri()
    paths = _run(ExportPackageTech()._execute(data))
    summary = json.loads(Path(paths["run_summary_json"]).read_text(encoding="utf-8"))
    assert summary["artifact_paths"]["html_report"] == str(html_file)


def test_run_summary_omits_html_report_when_unavailable(tmp_path: Path):
    """Regression: run_summary.json artifact_paths omits html_report when no html path on report."""
    import json

    data = _make_data(tmp_path)
    paths = _run(ExportPackageTech()._execute(data))
    summary = json.loads(Path(paths["run_summary_json"]).read_text(encoding="utf-8"))
    assert "html_report" not in summary["artifact_paths"]


def test_flat_platform_config_per_artifact_flags_respected(tmp_path: Path):
    """Regression: per-artifact flags work with flat platform-level config, not nested AppConfig."""
    data = {
        "report": {"topic": "test", "platform": "youtube", "items_top_n": []},
        "config": {
            "max_items": 10,
            "export": {
                "enabled": True,
                "sources_csv": False,
                "comments_csv": True,
                "methodology_md": False,
                "run_summary_json": True,
            },
        },
        "stem": "regression",
        "reports_dir": tmp_path,
    }
    paths = _run(ExportPackageTech()._execute(data))
    assert "sources_csv" not in paths
    assert "methodology_md" not in paths
    assert "comments_csv" in paths
    assert "run_summary_json" in paths
