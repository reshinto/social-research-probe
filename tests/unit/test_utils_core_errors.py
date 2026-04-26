"""Tests for utils.core.errors."""

from __future__ import annotations

from social_research_probe.utils.core.errors import (
    AdapterError,
    DuplicateError,
    MigrationError,
    SrpError,
    SynthesisError,
    ValidationError,
)


def test_base_exit_code():
    assert SrpError.exit_code == 2


def test_validation_exit_code():
    assert ValidationError.exit_code == 2
    assert issubclass(ValidationError, SrpError)


def test_duplicate_exit_code():
    assert DuplicateError.exit_code == 3
    assert issubclass(DuplicateError, SrpError)


def test_adapter_exit_code():
    assert AdapterError.exit_code == 4
    assert issubclass(AdapterError, SrpError)


def test_synthesis_exit_code():
    assert SynthesisError.exit_code == 4
    assert issubclass(SynthesisError, SrpError)


def test_migration_exit_code():
    assert MigrationError.exit_code == 5
    assert issubclass(MigrationError, SrpError)
