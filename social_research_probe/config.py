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
    FreeTextRunnerName,
    JSONObject,
    RunnerName,
    RunnerSettings,
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
        "backend": "host",
        "max_claims_per_item": 5,
        "max_claims_per_session": 15,
    },
    "platforms": {
        "youtube": {
            "recency_days": 90,
            "max_items": 20,
            "cache_ttl_search_hours": 6,
            "cache_ttl_channel_hours": 24,
        },
    },
    "scoring": {"weights": {}},
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
        """Return the configured free-text runner, or None when LLM is disabled.

        Returns the runner name for any concrete provider (claude, gemini, codex,
        local). Returns None only when runner is ``none``, so callers can treat
        None as "disabled" rather than "fall back to ensemble".
        """
        if self.llm_runner in {"claude", "gemini", "codex", "local"}:
            return self.llm_runner
        return None

    @property
    def default_structured_runner(self) -> RunnerName:
        """Return the configured runner for structured JSON tasks.

        Returns the raw configured value including ``none``. Callers must gate
        on health_check() before invoking, so ``none`` propagates correctly as
        "disabled" instead of silently falling back to another provider.
        """
        return self.llm_runner

    def platform_defaults(self, name: str) -> AdapterConfig:
        """Return a copy of the per-platform defaults used to build adapter config."""
        return dict(self.raw["platforms"].get(name, {}))


def load_active_config() -> Config:
    """Load config for the currently active data dir resolution chain."""
    return Config.load(resolve_data_dir(None))
