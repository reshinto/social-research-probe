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
    DatabaseConfigSection,
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
        "claude": {"extra_flags": ["--model", "claude-haiku-4-5"]},
        "gemini": {"extra_flags": ["--model", "gemini-2.5-flash-lite"]},
        "codex": {"binary": "codex", "extra_flags": ["--model", "gpt-5.4"]},
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
            "comments": {
                "enabled": True,
                "max_videos": 5,
                "max_comments_per_video": 20,
                "order": "relevance",
            },
            "claims": {
                "enabled": True,
                "max_claims_per_source": 10,
                "use_llm": False,
                "max_claim_chars": 500,
            },
            "export": {
                "enabled": True,
                "sources_csv": True,
                "comments_csv": True,
                "claims_csv": True,
                "methodology_md": True,
                "run_summary_json": True,
            },
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
            "comments": True,
            "claims": True,
            "export": True,
            "persist": True,
        },
    },
    "services": {
        "youtube": {
            "sourcing": {"youtube": True},
            "classifying": {"source_class": True},
            "scoring": {"score": True},
            "enriching": {
                "transcript": True,
                "text_surrogate": True,
                "summary": True,
                "comments": True,
                "claims": True,
            },
            "corroborating": {"corroborate": True},
            "analyzing": {"statistics": True, "charts": True},
            "synthesizing": {"synthesis": True},
            "reporting": {"html": True, "audio": True, "export": True},
        },
        # Legacy keys still looked up by internal config methods.
        "corroborate": {"corroboration": True},
        "enrich": {"llm": True},
        "persistence": {"sqlite": True},
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
        "youtube_comments": True,
        "export_package": True,
        "sqlite_persist": True,
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
    "database": {
        "enabled": True,
        "path": "",
        "persist_transcript_text": False,
        "persist_comment_text": True,
    },
}


def _collect_service_names(node: object) -> set[str]:
    """Collect service names from nested config sections for compatibility checks.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Args:
        node: Nested config dictionary or leaf value being scanned.

    Returns:
        Set of names found while walking the input structure.

    Examples:
        Input:
            _collect_service_names(
                node={"youtube": {"comments": {"enabled": True}}},
            )
        Output:
            {"comments", "html"}
    """
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
    """Resolve data dir, set SRP_DATA_DIR, and warm the config singleton.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Args:
        flag: Optional data-directory path supplied by the CLI.
        cwd: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            resolve_data_dir(
                flag=".skill-data",
                cwd=Path(".skill-data"),
            )
        Output:
            None
    """
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
    """Recursively merge override into base without mutating either input.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Args:
        base: Default dictionary used as the merge starting point.
        override: User-provided dictionary whose values should replace defaults.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _deep_merge(
                base={"llm": {"runner": "none"}},
                override={"llm": {"runner": "codex"}},
            )
        Output:
            {"llm": {"runner": "codex"}}
    """
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


@dataclass(frozen=True)
class Config:
    """Typed shape for config data.

    Examples:
        Input:
            Config
        Output:
            Config(data_dir=Path(".skill-data"))
    """

    data_dir: Path
    raw: AppConfig = field(default_factory=lambda: copy.deepcopy(DEFAULT_CONFIG))

    @classmethod
    def load(cls, data_dir: Path) -> Config:
        """Load the requested project state or configuration object.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            data_dir: Filesystem location used to read, write, or resolve project data.

        Returns:
            Config object with defaults, user overrides, and data directory resolved.

        Examples:
            Input:
                Config.load(
                    data_dir=Path(".skill-data"),
                )
            Output:
                Config(data_dir=Path(".skill-data"))
        """
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
        """Return the configured LLM runner name used to select the default adapter.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured llm runner setting.

        Examples:
            Input:
                config.llm_runner
            Output:
                "codex"
        """
        return self.raw["llm"]["runner"]

    @property
    def llm_timeout_seconds(self) -> int:
        """Return the configured LLM subprocess timeout as an integer.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured llm timeout seconds setting.

        Examples:
            Input:
                config.llm_timeout_seconds
            Output:
                180
        """
        return int(self.raw["llm"]["timeout_seconds"])

    @property
    def corroboration_provider(self) -> str:
        """Return the configured corroboration provider name.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured corroboration provider setting.

        Examples:
            Input:
                config.corroboration_provider
            Output:
                "brave"
        """
        return self.raw["corroboration"]["provider"]

    def llm_settings(self, name: RunnerName) -> RunnerSettings:
        """Return the llm config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                llm_settings(
                    name="codex",
                )
            Output:
                {"binary": "codex", "extra_flags": []}
        """
        if name == "none":
            return {}
        return dict(self.raw["llm"][name])

    @property
    def preferred_free_text_runner(self) -> FreeTextRunnerName | None:
        """Return the configured free-text runner, or None when LLM is disabled.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured preferred free text runner setting.

        Examples:
            Input:
                config.preferred_free_text_runner
            Output:
                "codex"
        """
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
        """Return the default LLM runner for structured responses.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured default structured runner setting.

        Examples:
            Input:
                config.default_structured_runner
            Output:
                "codex"
        """
        if self.llm_runner == "none":
            return "none"
        if not self.service_enabled("llm"):
            return "none"
        return self.llm_runner if self.technology_enabled(self.llm_runner) else "none"

    def platform_defaults(self, name: str) -> AdapterConfig:
        """Return the platforms config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                platform_defaults(
                    name="youtube",
                )
            Output:
                {"recency_days": 30, "max_items": 10}
        """
        return dict(self.raw["platforms"].get(name, {}))

    def apply_platform_overrides(self, overrides: dict) -> None:
        """Merge CLI overrides into all platform defaults in-place.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            overrides: Configuration or context values that control this run.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                apply_platform_overrides(
                    overrides={"enabled": True},
                )
            Output:
                None
        """
        for platform_data in self.raw["platforms"].values():
            if isinstance(platform_data, dict):
                platform_data.update(overrides)

    @property
    def stages(self) -> StagesConfigSection:
        """Return the stages config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured stages setting.

        Examples:
            Input:
                config.stages
            Output:
                {"youtube": {"fetch": True}}
        """
        return self.raw["stages"]

    @property
    def services(self) -> ServicesConfigSection:
        """Return the services config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured services setting.

        Examples:
            Input:
                config.services
            Output:
                {"youtube": {"enrichment": {"comments": True}}}
        """
        return self.raw["services"]

    @property
    def technologies(self) -> TechnologiesConfigSection:
        """Return the technologies config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured technologies setting.

        Examples:
            Input:
                config.technologies
            Output:
                {"youtube_api": True, "voicebox": True}
        """
        return self.raw["technologies"]

    @property
    def tunables(self) -> TunablesConfigSection:
        """Return the tunables config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured tunables setting.

        Examples:
            Input:
                config.tunables
            Output:
                {"scoring": {"trust_weight": 0.4}}
        """
        return self.raw["tunables"]

    @property
    def debug(self) -> DebugConfigSection:
        """Return the debug config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured debug setting.

        Examples:
            Input:
                config.debug
            Output:
                {"progress": True}
        """
        return self.raw["debug"]

    @property
    def voicebox(self) -> VoiceboxConfigSection:
        """Return the voicebox config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured voicebox setting.

        Examples:
            Input:
                config.voicebox
            Output:
                {"api_base": "http://127.0.0.1:5050"}
        """
        return self.raw["voicebox"]

    @property
    def database(self) -> DatabaseConfigSection:
        """Return the database config block through the typed Config API.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured database setting.

        Examples:
            Input:
                config.database
            Output:
                {"enabled": True, "path": "srp.db"}
        """
        return self.raw["database"]

    @property
    def database_path(self) -> Path:
        """Return the resolved path for srp.db.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Returns:
            The configured database path setting.

        Examples:
            Input:
                config.database_path
            Output:
                Path("report.html")
        """
        raw = (self.raw.get("database") or {}).get("path") or ""
        if not raw:
            return self.data_dir / "srp.db"
        p = Path(str(raw)).expanduser()
        return p if p.is_absolute() else (self.data_dir / p)

    def stage_enabled(self, platform: str, name: str) -> bool:
        """Return True iff the named stage is enabled for the given platform.

        Config access stays centralized so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            platform: Platform name, such as youtube or all, used to select config and pipeline
                      behavior.
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                stage_enabled(
                    platform="AI safety",
                    name="AI safety",
                )
            Output:
                True
        """
        platform_stages = self.stages.get(platform)
        if not isinstance(platform_stages, dict):
            return True
        flag = platform_stages.get(name)
        return bool(flag) if flag is not None else True

    def service_enabled(self, name: str) -> bool:
        """Return True iff the named service gate is enabled.

        Config access stays centralized so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                service_enabled(
                    name="comments",
                )
            Output:
                True
        """
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
        """Find a nested service flag in the compatibility config tree.

        Config access is centralized here so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            node: Nested config dictionary or leaf value being scanned.
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _find_service_value(
                    node={"youtube": {"comments": {"enabled": True}}},
                    name="comments",
                )
            Output:
                "AI safety"
        """
        for key, value in node.items():
            if key == name:
                return value
            if isinstance(value, dict):
                found = self._find_service_value(value, name)
                if found is not None:
                    return found
        return None

    def technology_enabled(self, name: str) -> bool:
        """Return True iff the named technology/provider is enabled.

        Config access stays centralized so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                technology_enabled(
                    name="AI safety",
                )
            Output:
                True
        """
        flag = self.technologies.get(name)
        return bool(flag) if flag is not None else False

    def debug_enabled(self, name: str) -> bool:
        """Return True iff the named debug gate is enabled.

        Config access stays centralized so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            name: Registry, config, or CLI name used to select the matching project value.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                debug_enabled(
                    name="AI safety",
                )
            Output:
                True
        """
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
        """Return True when the stage/service/technology chain permits execution.

        Config access stays centralized so callers do not need to know the TOML layout, environment
        fallbacks, or compatibility aliases.

        Args:
            platform: Platform name, such as youtube or all, used to select config and pipeline
                      behavior.
            stage: Registry, config, or CLI name used to select the matching project value.
            service: Registry, config, or CLI name used to select the matching project value.
            technology: Technology adapter exposing a stable name and execute method.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                allows(
                    platform="AI safety",
                    stage="comments",
                    service="summary",
                    technology=summary_adapter,
                )
            Output:
                True
        """
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
    """Resolve the active data dir path used by this command.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _active_data_dir()
        Output:
            Path("report.html")
    """
    if env := os.environ.get("SRP_DATA_DIR"):
        return Path(env).expanduser().resolve()
    return (Path.home() / ".social-research-probe").resolve()


def load_active_config(data_dir: Path | None = None) -> Config:
    """Load active config from disk or active configuration.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Args:
        data_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        Config object with defaults, user overrides, and data directory resolved.

    Examples:
        Input:
            load_active_config(
                data_dir=Path(".skill-data"),
            )
        Output:
            Config(data_dir=Path(".skill-data"))
    """
    resolved = data_dir if data_dir is not None else _active_data_dir()
    if resolved not in _config_cache:
        _config_cache[resolved] = Config.load(resolved)
    return _config_cache[resolved]


def reset_config_cache() -> None:
    """Clear the config cache — for use in tests only.

    Config access is centralized here so callers do not need to know the TOML layout, environment
    fallbacks, or compatibility aliases.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            reset_config_cache()
        Output:
            None
    """
    _config_cache.clear()
