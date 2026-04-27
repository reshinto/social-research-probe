"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService
from social_research_probe.technologies.scoring import ScoringComputeTech


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Delegates to scoring/compute.py via ScoringComputeTech.
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

    def _get_technologies(self):
        return [ScoringComputeTech()]
