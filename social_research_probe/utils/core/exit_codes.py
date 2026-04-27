"""Exit codes for CLI commands."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for command execution."""

    SUCCESS = 0
    ERROR = 2
