"""Exception hierarchy. Each subclass carries its spec §9 exit code."""

from __future__ import annotations


class SrpError(Exception):
    exit_code: int = 2


class ValidationError(SrpError):
    exit_code = 2


class DuplicateError(SrpError):
    exit_code = 3


class AdapterError(SrpError):
    exit_code = 4


class SynthesisError(SrpError):
    exit_code = 4


class MigrationError(SrpError):
    exit_code = 5
