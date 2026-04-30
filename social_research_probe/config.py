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

from social_research_probe.utils.core.types import (
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
        "claude": {"extra_flags": []},
        "gemini": {"extra_flags": []},
        "codex": {"binary": "codex", "extra_flags": []},
        "local": {},
    },
    "corroboration": {
        "provider": "auto",
        "max_claims_per_item": 5,
        "max_claims_per_session": 15,
    },
    "platforms": {
        "youtube": {
            "recency_days": 90,
            "max_items": 20,
            "enrich_top_n": 5,
        },
    },
    "scoring": {"weights": {}},
    "stages": {
        "youtube": {
            "fetch": True,
            "classify": True,
            "score": True,
            "transcript": True,
            "summary": True,
            "corroborate": True,
            "stats": True,
            "charts": True,
            "synthesis": True,
            "assemble": True,
            "structured_synthesis": True,
            "report": True,
            "narration": True,
        },
    },
    "services": {
        "youtube": {
            "sourcing": {"youtube": True},
            "classifying": {"source_class": True},
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
        "classifying": True,
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
        "llm_ensemble": True,
        "llm_synthesis": True,
        "html_render": True,
        "stats_per_target": True,
        "charts_suite": True,
        "scoring_compute": True,
        "youtube_search": True,
        "youtube_hydrate": True,
        "youtube_engagement": True,
        "corroboration_host": True,
        "mac_tts": True,
        "claim_extractor": True,
        "ai_slop_detector": True,
    },
    "tunables": {
        "summary_divergence_threshold": 0.4,
        "per_item_summary_words": 100,
    },
    "debug": {
        "technology_logs_enabled": True,
    },
    "voicebox": {
        "default_profile_name": "Jarvis",
        "api_base": "http://127.0.0.1:17493",
    },
}


def _collect_service_names(node: object) -> set[str]:
    """Return leaf service flag names declared by the current config schema."""
    if not isinstance(node, dict):
        return set()
    names: set[str] = set()
    for key, value in node.items():
        if isinstance(value, dict):
            names.update(_collect_service_names(value))
        else:
            names.add(str(key))
    return names


_KNOWN_SERVICE_NAMES = frozenset(_collect_service_names(DEFAULT_CONFIG["services"]))


def resolve_data_dir(flag: str | None, cwd: Path | None = None) -> None:
    """Resolve data dir, set SRP_DATA_DIR, and warm the config singleton."""
    if flag:
        resolved = Path(flag).expanduser().resolve()
    elif env := os.environ.get("SRP_DATA_DIR"):
        resolved = Path(env).expanduser().resolve()
    else:
        cwd = cwd or Path.cwd()
        local = cwd / ".skill-data"
        resolved = (
            local.resolve()
            if local.is_dir()
            else (Path.home() / ".social-research-probe").resolve()
        )
    os.environ["SRP_DATA_DIR"] = str(resolved)
    load_active_config(resolved)


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
    def corroboration_provider(self) -> str:
        """Return the configured corroboration provider name."""
        return self.raw["corroboration"]["provider"]

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
        if self.llm_runner in {
            "claude",
            "gemini",
            "codex",
            "local",
        } and self.technology_enabled(self.llm_runner):
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

    def apply_platform_overrides(self, overrides: dict) -> None:
        """Merge CLI overrides into all platform defaults in-place."""
        for platform_data in self.raw["platforms"].values():
            if isinstance(platform_data, dict):
                platform_data.update(overrides)

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

    def stage_enabled(self, platform: str, name: str) -> bool:
        """Return True iff the named stage is enabled for the given platform."""
        platform_stages = self.stages.get(platform)
        if not isinstance(platform_stages, dict):
            return True
        flag = platform_stages.get(name)
        return bool(flag) if flag is not None else True

    def service_enabled(self, name: str) -> bool:
        """Return True iff the named service gate is enabled."""
        if name not in _KNOWN_SERVICE_NAMES:
            return False
        for category in self.services.values():
            if isinstance(category, dict) and name in category:
                return bool(category[name])
            if isinstance(category, dict):
                value = self._find_service_value(category, name)
                if value is not None:
                    return bool(value)
        return False

    def _find_service_value(self, node: dict, name: str) -> object | None:
        for key, value in node.items():
            if key == name:
                return value
            if isinstance(value, dict):
                found = self._find_service_value(value, name)
                if found is not None:
                    return found
        return None

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
        platform: str | None = None,
        stage: str | None = None,
        service: str | None = None,
        technology: str | None = None,
    ) -> bool:
        """Return True when the stage/service/technology chain permits execution."""
        if stage is not None:
            if platform is None:
                return False
            if not self.stage_enabled(platform, stage):
                return False
        if service is not None and not self.service_enabled(service):
            return False
        return technology is None or self.technology_enabled(technology)


_config_cache: dict[Path, Config] = {}


def _active_data_dir() -> Path:
    if env := os.environ.get("SRP_DATA_DIR"):
        return Path(env).expanduser().resolve()
    return (Path.home() / ".social-research-probe").resolve()


def load_active_config(data_dir: Path | None = None) -> Config:
    """Return a cached Config for data_dir (or the active dir from SRP_DATA_DIR)."""
    resolved = data_dir if data_dir is not None else _active_data_dir()
    if resolved not in _config_cache:
        _config_cache[resolved] = Config.load(resolved)
    return _config_cache[resolved]


def reset_config_cache() -> None:
    """Clear the config cache — for use in tests only."""
    _config_cache.clear()
