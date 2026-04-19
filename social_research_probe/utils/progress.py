"""Progress logging to stderr.

All [srp] diagnostic messages go to stderr so they are visible in the
terminal without polluting stdout. In skill mode srp writes a JSON packet
to stdout that the host reads — any non-JSON bytes on stdout break parsing.
"""

from __future__ import annotations

import sys


def log(msg: str) -> None:
    """Print a [srp]-prefixed progress message to stderr."""
    print(msg, file=sys.stderr)
