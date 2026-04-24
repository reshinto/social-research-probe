"""Exit codes map to the spec §9 table."""

from __future__ import annotations

import pytest
from social_research_probe.errors import (
    AdapterError,
    DuplicateError,
    MigrationError,
    SrpError,
    ValidationError,
)


def test_base_error_defaults_to_exit_2():
    err = SrpError("generic")
    assert err.exit_code == 2
    assert str(err) == "generic"


@pytest.mark.parametrize(
    ("exc_cls", "expected_code"),
    [
        (ValidationError, 2),
        (DuplicateError, 3),
        (AdapterError, 4),
        (MigrationError, 5),
    ],
)
def test_subclass_exit_codes(exc_cls: type[SrpError], expected_code: int):
    assert exc_cls("x").exit_code == expected_code
    assert issubclass(exc_cls, SrpError)
