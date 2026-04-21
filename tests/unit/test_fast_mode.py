"""Tests for utils/fast_mode.py — env-var gate + preset constants."""

from __future__ import annotations

import pytest

from social_research_probe.utils import fast_mode


def test_fast_mode_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SRP_FAST_MODE", raising=False)
    assert fast_mode.fast_mode_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " On "])
def test_fast_mode_truthy_values_enable(monkeypatch, value):
    monkeypatch.setenv("SRP_FAST_MODE", value)
    assert fast_mode.fast_mode_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_fast_mode_falsy_values_disable(monkeypatch, value):
    monkeypatch.setenv("SRP_FAST_MODE", value)
    assert fast_mode.fast_mode_enabled() is False


def test_fast_mode_preset_caps_are_conservative():
    assert fast_mode.FAST_MODE_TOP_N == 3
    assert fast_mode.FAST_MODE_MAX_BACKENDS == 1
