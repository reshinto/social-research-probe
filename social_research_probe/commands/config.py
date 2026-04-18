"""srp config subcommand: non-secret config + secrets file management."""
from __future__ import annotations

import json
import os
import stat
import tomllib
from pathlib import Path
from typing import Any

from social_research_probe.config import Config
from social_research_probe.errors import ValidationError

SECRET_FILENAME = "secrets.toml"
CONFIG_FILENAME = "config.toml"

_PLATFORM_SECRETS: dict[str, list[str]] = {
    "youtube": ["youtube_api_key"],
}

_CORROBORATION_SECRETS: dict[str, list[str]] = {
    "exa": ["exa_api_key"],
    "brave": ["brave_api_key"],
    "tavily": ["tavily_api_key"],
}


def _env_key(name: str) -> str:
    return f"SRP_{name.upper()}"


def _read_secrets_file(data_dir: Path) -> dict[str, str]:
    path = data_dir / SECRET_FILENAME
    if not path.exists():
        return {}
    _check_perms(path)
    with path.open("rb") as f:
        parsed = tomllib.load(f)
    secrets = parsed.get("secrets", {})
    return {str(k): str(v) for k, v in secrets.items()}


def _check_perms(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        import sys
        print(
            f"warning: {path} has permissions {oct(mode)}; should be 0600",
            file=sys.stderr,
        )


def _write_secrets_file(data_dir: Path, secrets: dict[str, str]) -> None:
    path = data_dir / SECRET_FILENAME
    data_dir.mkdir(parents=True, exist_ok=True)
    prev_umask = os.umask(0o077)
    try:
        lines = ["[secrets]"]
        for key, val in sorted(secrets.items()):
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    finally:
        os.umask(prev_umask)


def read_secret(data_dir: Path, name: str) -> str | None:
    env_val = os.environ.get(_env_key(name))
    if env_val:
        return env_val
    secrets = _read_secrets_file(data_dir)
    return secrets.get(name)


def write_secret(data_dir: Path, name: str, value: str) -> None:
    secrets = _read_secrets_file(data_dir)
    secrets[name] = value
    _write_secrets_file(data_dir, secrets)


def unset_secret(data_dir: Path, name: str) -> None:
    secrets = _read_secrets_file(data_dir)
    secrets.pop(name, None)
    _write_secrets_file(data_dir, secrets)


def mask_secret(value: str) -> str:
    if len(value) < 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def show_config(data_dir: Path) -> str:
    cfg = Config.load(data_dir)
    secrets = _read_secrets_file(data_dir)
    lines = [
        f"data_dir: {data_dir}",
        f"config_file: {data_dir / CONFIG_FILENAME}",
        f"secrets_file: {data_dir / SECRET_FILENAME}",
        "",
        "[config]",
        json.dumps(cfg.raw, indent=2),
        "",
        "[secrets]",
    ]
    for name, val in sorted(secrets.items()):
        env = os.environ.get(_env_key(name))
        if env:
            lines.append(f"  {name}: {mask_secret(env)}  (from env)")
        else:
            lines.append(f"  {name}: {mask_secret(val)}  (from file)")
    return "\n".join(lines)


def write_config_value(data_dir: Path, dotted_key: str, value: str) -> None:
    parts = dotted_key.split(".")
    if len(parts) != 2:
        raise ValidationError(f"config key must be section.key, got {dotted_key!r}")
    section, key = parts

    path = data_dir / CONFIG_FILENAME
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open("rb") as f:
            existing = tomllib.load(f)

    existing.setdefault(section, {})[key] = value

    lines: list[str] = []
    for sec, entries in existing.items():
        lines.append(f"[{sec}]")
        for k, v in entries.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            else:
                lines.append(f"{k} = {v}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def check_secrets(
    data_dir: Path,
    *,
    needed_for: str | None,
    platform: str | None,
    corroboration: str | None,
) -> dict[str, list[str]]:
    required: list[str] = []

    if needed_for == "run-research" and platform:
        required.extend(_PLATFORM_SECRETS.get(platform, []))
    if corroboration:
        required.extend(_CORROBORATION_SECRETS.get(corroboration, []))

    all_known = {s for names in _PLATFORM_SECRETS.values() for s in names} | {
        s for names in _CORROBORATION_SECRETS.values() for s in names
    }
    optional = sorted(all_known - set(required))

    present = [name for name in (required + optional) if read_secret(data_dir, name) is not None]
    missing = [name for name in required if read_secret(data_dir, name) is None]

    return {
        "required": sorted(set(required)),
        "optional": optional,
        "present": sorted(set(present)),
        "missing": sorted(set(missing)),
    }
