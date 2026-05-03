"""Exception hierarchy. Each subclass carries its spec §9 exit code."""

from __future__ import annotations


class SrpError(Exception):
    """Srp error type.

    Examples:
        Input:
            SrpError
        Output:
            SrpError
    """

    exit_code: int = 2


class ValidationError(SrpError):
    """Validation error type.

    Examples:
        Input:
            ValidationError
        Output:
            ValidationError
    """

    exit_code = 2


class DuplicateError(SrpError):
    """Duplicate error type.

    Examples:
        Input:
            DuplicateError
        Output:
            DuplicateError
    """

    exit_code = 3


class AdapterError(SrpError):
    """Adapter error type.

    Examples:
        Input:
            AdapterError
        Output:
            AdapterError
    """

    exit_code = 4


class SynthesisError(SrpError):
    """Synthesis error type.

    Examples:
        Input:
            SynthesisError
        Output:
            SynthesisError
    """

    exit_code = 4


class MigrationError(SrpError):
    """Migration error type.

    Examples:
        Input:
            MigrationError
        Output:
            MigrationError
    """

    exit_code = 5
