"""Exit codes for CLI commands."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for command execution.

    Examples:
        Input:
            ExitCode
        Output:
            ExitCode
    """

    SUCCESS = 0
    ERROR = 2
