"""Allow running the CLI as ``python -m social_research_probe.cli``."""

import sys

from . import main

sys.exit(main())
