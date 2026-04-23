"""srp config subcommand: non-secret config + secrets file management."""

from __future__ import annotations

import json
import os
import stat
import tomllib
from pathlib import Path

from social_research_probe.config import DEFAULT_CONFIG, Config
from social_research_probe.errors import ValidationError
from social_research_probe.types import JSONObject, JSONScalar

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
    """Map a logical secret name to its environment-variable override name."""
    return f"SRP_{name.upper()}"


def _read_secrets_file(data_dir: Path) -> dict[str, str]:
    """Read secrets.toml when it exists and return a plain string mapping."""
    path = data_dir / SECRET_FILENAME
    if not path.exists():
        return {}
    _check_perms(path)
    with path.open("rb") as f:
        parsed = tomllib.load(f)
    secrets = parsed.get("secrets", {})
    return {str(k): str(v) for k, v in secrets.items()}


def _check_perms(path: Path) -> None:
    """Warn when the secrets file is group- or world-readable."""
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        import sys

        print(
            f"warning: {path} has permissions {oct(mode)}; should be 0600",
            file=sys.stderr,
        )


def _write_secrets_file(data_dir: Path, secrets: dict[str, str]) -> None:
    """Persist secrets.toml with restrictive permissions."""
    path = data_dir / SECRET_FILENAME
    data_dir.mkdir(parents=True, exist_ok=True)
    prev_umask = os.umask(0o077)
    try:
        lines = ["[secrets]"]
        for key, val in sorted(secrets.items()):
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    finally:
        os.umask(prev_umask)


def read_secret(data_dir: Path, name: str) -> str | None:
    """Read a secret, preferring an environment override when present."""
    env_val = os.environ.get(_env_key(name))
    if env_val:
        return env_val
    secrets = _read_secrets_file(data_dir)
    return secrets.get(name)


def write_secret(data_dir: Path, name: str, value: str) -> None:
    """Set or replace one secret value in secrets.toml."""
    secrets = _read_secrets_file(data_dir)
    secrets[name] = value
    _write_secrets_file(data_dir, secrets)


def unset_secret(data_dir: Path, name: str) -> None:
    """Remove one secret from secrets.toml if present."""
    secrets = _read_secrets_file(data_dir)
    secrets.pop(name, None)
    _write_secrets_file(data_dir, secrets)


def mask_secret(value: str) -> str:
    """Mask a secret so operators can confirm presence without leaking it."""
    if len(value) < 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def show_config(data_dir: Path) -> str:
    """Render the merged config plus masked secret status for CLI display."""
    cfg = Config.load(data_dir)
    display_config = {
        key: value for key, value in cfg.raw.items() if key not in {"features", "logging"}
    }
    secrets = _read_secrets_file(data_dir)
    lines = [
        f"data_dir: {data_dir}",
        f"config_file: {data_dir / CONFIG_FILENAME}",
        f"secrets_file: {data_dir / SECRET_FILENAME}",
        "",
        "[config]",
        json.dumps(display_config, indent=2),
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


def _parse_scalar_value(value: str) -> JSONScalar:
    """Best-effort parse of CLI scalar values before writing TOML."""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _format_toml_value(value: object) -> str:
    """Serialise a supported scalar or list value into TOML syntax."""
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    raise ValidationError(f"unsupported config value type: {type(value).__name__}")


def _emit_table(name: str, entries: JSONObject, lines: list[str]) -> None:
    """Render one TOML table, recursing into nested tables afterwards."""
    lines.append(f"[{name}]")
    child_tables: list[tuple[str, JSONObject]] = []
    for key, value in entries.items():
        if isinstance(value, dict):
            child_tables.append((key, value))
            continue
        lines.append(f"{key} = {_format_toml_value(value)}")
    lines.append("")
    for child_name, child_entries in child_tables:
        _emit_table(f"{name}.{child_name}", child_entries, lines)


def _order_like_template(data: JSONObject, template: JSONObject) -> JSONObject:
    """Return *data* reordered to match *template* first, preserving extras last."""
    ordered: JSONObject = {}
    for key, template_value in template.items():
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, dict) and isinstance(template_value, dict):
            ordered[key] = _order_like_template(value, template_value)
        else:
            ordered[key] = value
    for key, value in data.items():
        if key in ordered:
            continue
        if isinstance(value, dict):
            ordered[key] = _order_like_template(value, {})
        else:
            ordered[key] = value
    return ordered


def _set_nested_value(config: JSONObject, parts: list[str], value: JSONScalar) -> None:
    """Create any missing tables and assign the final scalar value."""
    current = config
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def write_config_value(data_dir: Path, dotted_key: str, value: str) -> None:
    """Write one config value, supporting nested dotted keys like llm.codex.model."""
    parts = dotted_key.split(".")
    if len(parts) < 2 or any(not part for part in parts):
        raise ValidationError(
            f"config key must be dotted path like section.key, got {dotted_key!r}"
        )

    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / CONFIG_FILENAME
    existing: JSONObject = {}
    if path.exists():
        with path.open("rb") as f:
            existing = tomllib.load(f)

    _set_nested_value(existing, parts, _parse_scalar_value(value))
    ordered = _order_like_template(existing, DEFAULT_CONFIG)

    lines: list[str] = []
    for sec, entries in ordered.items():
        if not isinstance(entries, dict):
            raise ValidationError(f"top-level config section {sec!r} must be a table")
        _emit_table(sec, entries, lines)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def check_secrets(
    data_dir: Path,
    *,
    needed_for: str | None,
    platform: str | None,
    corroboration: str | None,
) -> dict[str, list[str]]:
    """Report which secrets are required, optional, present, and missing."""
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
