"""Tests for suggest_topics, suggest_purposes, render, corroborate_claims, install_skill, setup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Other test modules import command submodules with the same name as functions
# in commands/__init__.py; that import binds the submodule to the package and
# clobbers the function. Restore the function attributes for this module.
import social_research_probe.commands as _commands_pkg
from social_research_probe.commands import (
    add_pending_suggestions as _fn_stage_suggestions,
)
from social_research_probe.commands import (
    corroborate_claims,
    install_skill,
    render,
    setup,
    suggest_purposes,
    suggest_topics,
)
from social_research_probe.commands import (
    list_purposes as _fn_show_purposes,
)
from social_research_probe.commands import (
    list_topics as _fn_show_topics,
)
from social_research_probe.utils.core.errors import ValidationError


@pytest.fixture(autouse=True)
def _restore_command_functions():
    _commands_pkg.show_topics = _fn_show_topics
    _commands_pkg.show_purposes = _fn_show_purposes
    _commands_pkg.stage_suggestions = _fn_stage_suggestions
    yield


@pytest.fixture
def isolated(tmp_path: Path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.default_structured_runner = "claude"
    cfg.service_enabled.return_value = True
    cfg.voicebox = {"api_base": "http://x"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


class TestSuggestTopics:
    def test_resolve_runner_none_when_disabled(self, isolated, monkeypatch):
        cfg = MagicMock()
        cfg.default_structured_runner = "none"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            assert suggest_topics._resolve_runner_or_none() is None

    def test_seed_drafts_when_no_runner(self):
        drafts = suggest_topics._seed_drafts(existing=[], count=3)
        assert len(drafts) == 3
        assert all("value" in d and "reason" in d for d in drafts)

    def test_extract_drafts(self):
        out = suggest_topics._extract_drafts(
            {"suggestions": [{"value": "x", "reason": "r"}, {"value": "y"}]}
        )
        assert out == [{"value": "x", "reason": "r"}, {"value": "y", "reason": ""}]

    def test_build_prompt(self):
        out = suggest_topics._build_prompt(["a"], 5)
        assert "a" in out

    def test_run(self, isolated, capsys, monkeypatch):
        monkeypatch.setattr(
            suggest_topics, "_call_llm", lambda p, r: {"suggestions": [{"value": "ai"}]}
        )
        ns = argparse.Namespace(count=3, output="json")
        assert suggest_topics.run(ns) == 0


class TestSuggestPurposes:
    def test_validate_disabled(self):
        cfg = MagicMock()
        cfg.default_structured_runner = "none"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with pytest.raises(ValidationError):
                suggest_purposes._validate_llm_runner()

    def test_extract_drafts(self):
        out = suggest_purposes._extract_drafts({"suggestions": [{"name": "x", "method": "m"}]})
        assert out == [{"name": "x", "method": "m"}]

    def test_build_prompt(self):
        out = suggest_purposes._build_prompt([], 5)
        assert "(none yet)" in out

    def test_run(self, isolated, capsys, monkeypatch):
        monkeypatch.setattr(
            suggest_purposes,
            "_call_llm",
            lambda p, r: {"suggestions": [{"name": "p", "method": "M"}]},
        )
        ns = argparse.Namespace(count=3, output="json")
        assert suggest_purposes.run(ns) == 0


class TestRender:
    def test_load_invalid_path(self):
        with pytest.raises(ValidationError):
            render._load_report("/nonexistent/path.json")

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        with pytest.raises(ValidationError):
            render._load_report(str(path))

    def test_load_non_object(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text("[]")
        with pytest.raises(ValidationError):
            render._load_report(str(path))

    def test_load_envelope_unwraps(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text(json.dumps({"kind": "synthesis", "report": {"a": 1}}))
        out = render._load_report(str(path))
        assert out == {"a": 1}

    def test_extract_scores(self):
        out = render._extract_overall_scores(
            {"items_top_n": [{"scores": {"overall": 0.5}}, {"scores": {}}]}
        )
        assert out == [0.5, 0.0]

    def test_run(self, tmp_path, capsys):
        path = tmp_path / "report.json"
        path.write_text(
            json.dumps({"items_top_n": [{"scores": {"overall": v}} for v in (0.1, 0.2, 0.3)]})
        )
        rc = render.run(str(path), output_dir=str(tmp_path))
        assert rc == 0


class TestCorroborateClaims:
    def test_validate_disabled(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = False
        with (
            patch(
                "social_research_probe.commands.corroborate_claims.load_active_config",
                return_value=cfg,
            ),
            pytest.raises(ValidationError),
        ):
            corroborate_claims._validate_corroboration_config()

    def test_load_claims_bad(self):
        with pytest.raises(ValidationError):
            corroborate_claims._load_claims("/nonexistent/x.json")

    def test_load_claims(self, tmp_path):
        path = tmp_path / "c.json"
        path.write_text(json.dumps({"claims": [{"text": "x"}]}))
        assert corroborate_claims._load_claims(str(path)) == [{"text": "x"}]

    def test_write_output_stdout(self, capsys):
        corroborate_claims._write_output([{"a": 1}], None)
        assert "a" in capsys.readouterr().out

    def test_write_output_file(self, tmp_path):
        out = tmp_path / "o.json"
        corroborate_claims._write_output([{"a": 1}], str(out))
        data = json.loads(out.read_text())
        assert data["results"] == [{"a": 1}]

    def test_run(self, tmp_path, monkeypatch):
        path = tmp_path / "c.json"
        path.write_text(json.dumps({"claims": [{"text": "x"}]}))

        async def fake(claim, providers):
            return {"verdict": "x", "claim_text": claim.text}

        monkeypatch.setattr(
            "social_research_probe.commands.corroborate_claims.corroborate_claim", fake
        )
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            rc = corroborate_claims.run(str(path), ["exa"])
        assert rc == 0


class TestInstallSkill:
    def test_validate_target_outside_raises(self, tmp_path):
        with pytest.raises(ValidationError):
            install_skill._validate_target(tmp_path / "out")

    def test_validate_target_inside_ok(self):
        from pathlib import Path as P

        install_skill._validate_target(P.home() / ".claude" / "skills" / "srp")

    def test_get_runner_choice_skip(self, capsys):
        out = install_skill._get_runner_choice(_input=lambda p: "")
        assert out is None

    def test_get_runner_choice_invalid(self, capsys):
        out = install_skill._get_runner_choice(_input=lambda p: "abc")
        assert out is None

    def test_get_runner_choice_oob(self, capsys):
        out = install_skill._get_runner_choice(_input=lambda p: "999")
        assert out is None

    def test_get_runner_choice_valid(self, capsys):
        out = install_skill._get_runner_choice(_input=lambda p: "1")
        assert out in {n for n, _, _ in install_skill._RUNNER_CHOICES}

    def test_get_runner_choice_eof(self, capsys):
        def _eof(p):
            raise EOFError

        assert install_skill._get_runner_choice(_input=_eof) is None

    def test_prompt_single_secret_skip(self):
        cfg = MagicMock()
        cfg.data_dir = Path("/tmp/x")
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch(
                "social_research_probe.commands.install_skill.read_secret",
                create=True,
                return_value=None,
            ):
                pass
        # call directly with stub input
        val, cont = install_skill._prompt_for_single_secret("n", "desc", "url", _input=lambda p: "")
        assert val is None and cont is True

    def test_prompt_single_secret_eof(self):
        def _eof(p):
            raise EOFError

        val, cont = install_skill._prompt_for_single_secret("n", "d", "", _input=_eof)
        assert val is None and cont is False


class TestSetup:
    def test_run(self, monkeypatch, capsys):
        monkeypatch.setattr(setup, "_prompt_for_secrets", lambda: None)
        monkeypatch.setattr(setup, "_copy_config_example", lambda: None)
        monkeypatch.setattr(setup, "_prompt_for_runner", lambda: None)
        assert setup.run() == 0
