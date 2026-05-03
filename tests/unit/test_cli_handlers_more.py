"""Tests for cli/handlers wrapper functions."""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

# Other tests import submodules with same names as functions in commands/__init__.py.
# Capture and restore the original function references each test.
import social_research_probe.commands as _commands_pkg
from social_research_probe.cli import handlers

_ORIG = {}
for _name in ("show_topics", "show_purposes", "stage_suggestions"):
    val = getattr(_commands_pkg, _name, None)
    if callable(val) and not hasattr(val, "__path__"):
        _ORIG[_name] = val


@pytest.fixture(autouse=True)
def _restore_command_fns():
    for k, v in _ORIG.items():
        setattr(_commands_pkg, k, v)
    yield


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_handle_update_topics():
    with patch("social_research_probe.commands.update_topics.run", return_value=0) as m:
        assert handlers._handle_update_topics(_ns()) == 0
    m.assert_called_once()


def test_handle_show_topics():
    with patch("social_research_probe.commands.show_topics.run", return_value=0):
        assert handlers._handle_show_topics(_ns()) == 0


def test_handle_update_purposes():
    with patch("social_research_probe.commands.update_purposes.run", return_value=0):
        assert handlers._handle_update_purposes(_ns()) == 0


def test_handle_show_purposes():
    with patch("social_research_probe.commands.show_purposes.run", return_value=0):
        assert handlers._handle_show_purposes(_ns()) == 0


def test_handle_suggest_topics():
    with patch("social_research_probe.commands.suggest_topics.run", return_value=0):
        assert handlers._handle_suggest_topics(_ns()) == 0


def test_handle_suggest_purposes():
    with patch("social_research_probe.commands.suggest_purposes.run", return_value=0):
        assert handlers._handle_suggest_purposes(_ns()) == 0


def test_handle_show_pending():
    with patch("social_research_probe.commands.show_pending.run", return_value=0):
        assert handlers._handle_show_pending(_ns()) == 0


def test_handle_apply_pending():
    with patch("social_research_probe.commands.apply_pending.run", return_value=0):
        assert handlers._handle_apply_pending(_ns()) == 0


def test_handle_discard_pending():
    with patch("social_research_probe.commands.discard_pending.run", return_value=0):
        assert handlers._handle_discard_pending(_ns()) == 0


def test_handle_stage_suggestions():
    with patch("social_research_probe.commands.stage_suggestions.run", return_value=0):
        assert handlers._handle_stage_suggestions(_ns()) == 0


def test_handle_corroborate_claims():
    with patch("social_research_probe.commands.corroborate_claims.run", return_value=0) as m:
        assert (
            handlers._handle_corroborate_claims(_ns(input="i", providers="exa,brave", output="o"))
            == 0
        )
    args, _kwargs = m.call_args
    assert args[0] == "i" and args[1] == ["exa", "brave"]


def test_handle_render():
    with patch("social_research_probe.commands.render.run", return_value=0):
        assert handlers._handle_render(_ns(packet="p", output_dir="d")) == 0


def test_handle_research():
    with patch("social_research_probe.commands.research.run", return_value=0):
        assert handlers._handle_research(_ns()) == 0


def test_handle_install_skill():
    with patch("social_research_probe.commands.install_skill.run", return_value=0):
        assert handlers._handle_install_skill(_ns(target=None)) == 0


def test_handle_setup():
    with patch("social_research_probe.commands.setup.run", return_value=0):
        assert handlers._handle_setup(_ns()) == 0


def test_handle_report():
    with patch("social_research_probe.commands.report.run", return_value=0):
        assert (
            handlers._handle_report(
                _ns(
                    packet="p",
                    compiled_synthesis_path=None,
                    opportunity_analysis_path=None,
                    final_summary_path=None,
                    out=None,
                )
            )
            == 0
        )


def test_handle_serve_report():
    with patch("social_research_probe.commands.serve_report.run", return_value=0):
        assert (
            handlers._handle_serve_report(
                _ns(
                    report="r",
                    host="127.0.0.1",
                    port=8000,
                    voicebox_base=None,
                )
            )
            == 0
        )


def test_dispatch_config():
    with patch("social_research_probe.commands.config.run", return_value=0):
        assert handlers._dispatch_config(_ns()) == 0


def test_dispatch_db():
    with patch("social_research_probe.commands.db.run", return_value=0):
        assert handlers._dispatch_db(_ns()) == 0


def test_dispatch_claims():
    with patch("social_research_probe.commands.claims.run", return_value=0):
        assert handlers._dispatch_claims(_ns()) == 0


def test_dispatch_compare():
    with patch("social_research_probe.commands.compare.run", return_value=0):
        assert handlers._dispatch_compare(_ns()) == 0
