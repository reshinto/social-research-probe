"""Progress logging to stderr.

All [srp] diagnostic messages go to stderr so they are visible in the
terminal without polluting stdout. The research command emits a JSON packet
envelope on stdout, so any non-JSON bytes there break parsing.
"""

from __future__ import annotations

import sys


def log(msg: str) -> None:
    """Print a [srp]-prefixed progress message to stderr."""
    print(msg, file=sys.stderr)
