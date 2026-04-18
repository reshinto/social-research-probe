"""Allow running social_research_probe as a module."""

from __future__ import annotations

import sys

from social_research_probe.cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
