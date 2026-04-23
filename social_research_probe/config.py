"""Data-dir resolution and typed config.toml loading.

This module owns non-secret runtime configuration. Secret material stays in the
separate secrets file handled by ``commands/config.py``.
"""

from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from social_research_probe.types import (
    AdapterConfig,
    AppConfig,
    DebugConfigSection,
    FreeTextRunnerName,
    JSONObject,
    RunnerName,
    RunnerSettings,
    ServicesConfigSection,
    StagesConfigSection,
    TechnologiesConfigSection,
    TunablesConfigSection,
    VoiceboxConfigSection,
)

DEFAULT_CONFIG: AppConfig = {
    "llm": {
        "runner": "none",
        "timeout_seconds": 60,
        "claude": {"model": "sonnet", "extra_flags": []},
        "gemini": {"model": "gemini-2.5-pro", "extra_flags": []},
        "codex": {"binary": "codex", "model": "gpt-4o", "extra_flags": []},
        "local": {"binary": "ollama", "model": "llama3.1:8b", "extra_flags": []},
    },
    "corroboration": {
        "backend": "auto",
        "max_claims_per_item": 5,
        "max_claims_per_session": 15,
    },
    "platforms": {
        "youtube": {
            "recency_days": 90,
            "max_items": 20,
            "enrich_top_n": 5,
            "cache_ttl_search_hours": 6,
            "cache_ttl_channel_hours": 24,
        },
    },
    "scoring": {"weights": {}},
    "stages": {
        "fetch": True,
        "score": True,
        "enrich": True,
        "corroborate": True,
        "analyze": True,
    },
    "services": {
        "youtube": {
            "sourcing": {"youtube": True},
            "scoring": {"score": True},
            "enriching": {"transcript": True, "summary": True},
            "corroborating": {"corroborate": True},
            "analyzing": {"statistics": True, "charts": True},
            "synthesizing": {"synthesis": True},
            "reporting": {"html": True, "audio": True},
        },
        # Legacy keys still looked up by internal config methods.
        "corroborate": {"corroboration": True},
        "enrich": {"llm": True},
    },
    "technologies": {
        "youtube_api": True,
        "youtube_transcript_api": True,
        "whisper": True,
        "yt_dlp": True,
        "voicebox": True,
        "claude": False,
        "gemini": False,
        "codex": False,
        "local": False,
        "llm_search": True,
        "exa": True,
        "brave": True,
        "tavily": True,
    },
    "tunables": {
        "summary_divergence_threshold": 0.4,
        "per_item_summary_words": 100,
    },
    "debug": {
        "technology_logs_enabled": False,
    },
    "voicebox": {
        "default_profile_name": "Jarvis",
    },
}


def resolve_data_dir(flag: str | None, cwd: Path | None = None) -> Path:
    """Resolve data dir in precedence: flag > env > cwd/.skill-data > ~/.social-research-probe."""
    if flag:
        return Path(flag).expanduser().resolve()
    if env := os.environ.get("SRP_DATA_DIR"):
        return Path(env).expanduser().resolve()
    cwd = cwd or Path.cwd()
    local = cwd / ".skill-data"
    if local.is_dir():
        return local.resolve()
    return (Path.home() / ".social-research-probe").resolve()


def _deep_merge(base: JSONObject, override: JSONObject) -> JSONObject:
    """Recursively merge override into base without mutating either input."""
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


@dataclass(frozen=True)
class Config:
    data_dir: Path
    raw: AppConfig = field(default_factory=lambda: copy.deepcopy(DEFAULT_CONFIG))

    @classmethod
    def load(cls, data_dir: Path) -> Config:
        """Load config.toml from data_dir and merge it over DEFAULT_CONFIG."""
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = data_dir / "config.toml"
        merged = copy.deepcopy(DEFAULT_CONFIG)
        if cfg_path.exists():
            with cfg_path.open("rb") as f:
                user = tomllib.load(f)
            merged = _deep_merge(merged, user)
        return cls(data_dir=data_dir, raw=merged)

    @property
    def llm_runner(self) -> RunnerName:
        """Return the configured default LLM runner name."""
        return self.raw["llm"]["runner"]

    @property
    def llm_timeout_seconds(self) -> int:
        """Return the configured LLM subprocess timeout as an integer."""
        return int(self.raw["llm"]["timeout_seconds"])

    @property
    def corroboration_backend(self) -> str:
        """Return the configured corroboration backend name."""
        return self.raw["corroboration"]["backend"]

    def llm_settings(self, name: RunnerName) -> RunnerSettings:
        """Return the nested settings block for one runner.

        ``none`` has no dedicated settings block, so it returns an empty dict.
        """
        if name == "none":
            return {}
        return dict(self.raw["llm"][name])

    @property
    def preferred_free_text_runner(self) -> FreeTextRunnerName | None:
        """Return the configured free-text runner, or None when LLM is disabled."""
        if not self.service_enabled("llm"):
            return None
        if self.llm_runner in {"claude", "gemini", "codex", "local"} and self.technology_enabled(
            self.llm_runner
        ):
            return self.llm_runner
        return None

    @property
    def default_structured_runner(self) -> RunnerName:
        """Return the configured runner for structured JSON tasks."""
        if self.llm_runner == "none":
            return "none"
        if not self.service_enabled("llm"):
            return "none"
        return self.llm_runner if self.technology_enabled(self.llm_runner) else "none"

    def platform_defaults(self, name: str) -> AdapterConfig:
        """Return a copy of the per-platform defaults used to build adapter config."""
        return dict(self.raw["platforms"].get(name, {}))

    @property
    def stages(self) -> StagesConfigSection:
        """Return the stage-level gates."""
        return self.raw["stages"]

    @property
    def services(self) -> ServicesConfigSection:
        """Return the service-level gates."""
        return self.raw["services"]

    @property
    def technologies(self) -> TechnologiesConfigSection:
        """Return the technology/provider gates."""
        return self.raw["technologies"]

    @property
    def tunables(self) -> TunablesConfigSection:
        """Return the tunables section with numeric thresholds."""
        return self.raw["tunables"]

    @property
    def debug(self) -> DebugConfigSection:
        """Return the debug/logging switches."""
        return self.raw["debug"]

    @property
    def voicebox(self) -> VoiceboxConfigSection:
        """Return the Voicebox renderer defaults."""
        return self.raw["voicebox"]

    def stage_enabled(self, name: str) -> bool:
        """Return True iff the named stage is enabled."""
        flag = self.stages.get(name)
        return bool(flag) if flag is not None else False

    def service_enabled(self, name: str) -> bool:
        """Return True iff the named service gate is enabled."""
        for category in self.services.values():
            if isinstance(category, dict) and name in category:
                return bool(category[name])
        return False

    def technology_enabled(self, name: str) -> bool:
        """Return True iff the named technology/provider is enabled."""
        flag = self.technologies.get(name)
        return bool(flag) if flag is not None else False

    def debug_enabled(self, name: str) -> bool:
        """Return True iff the named debug gate is enabled."""
        flag = self.debug.get(name)
        return bool(flag) if flag is not None else False

    def allows(
        self,
        *,
        stage: str | None = None,
        service: str | None = None,
        technology: str | None = None,
    ) -> bool:
        """Return True when the stage/service/technology chain permits execution."""
        if stage is not None and not self.stage_enabled(stage):
            return False
        if service is not None and not self.service_enabled(service):
            return False
        return technology is None or self.technology_enabled(technology)


def load_active_config() -> Config:
    """Load config for the currently active data dir resolution chain."""
    return Config.load(resolve_data_dir(None))
