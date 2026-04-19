"""Data-dir resolution + config.toml loading. Does NOT read secrets — see secrets.py."""

from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {"runner": "none", "timeout_seconds": 60},
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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
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
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, data_dir: Path) -> Config:
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = data_dir / "config.toml"
        merged = copy.deepcopy(DEFAULT_CONFIG)
        if cfg_path.exists():
            with cfg_path.open("rb") as f:
                user = tomllib.load(f)
            merged = _deep_merge(merged, user)
        return cls(data_dir=data_dir, raw=merged)

    @property
    def llm_runner(self) -> str:
        return self.raw["llm"]["runner"]

    @property
    def llm_timeout_seconds(self) -> int:
        return int(self.raw["llm"]["timeout_seconds"])

    @property
    def corroboration_backend(self) -> str:
        return self.raw["corroboration"]["backend"]

    def platform_defaults(self, name: str) -> dict[str, Any]:
        return dict(self.raw["platforms"].get(name, {}))
