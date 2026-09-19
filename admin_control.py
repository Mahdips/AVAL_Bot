"""Safe configuration and service controls for the Web Admin Panel."""

from __future__ import annotations

import os
import re
from pathlib import Path

SERVICE_NAMES = {"bot": "aval-bot", "web": "aval-bot-web"}
ALLOWED_ACTIONS = {"start", "stop", "restart", "remove", "status"}
ALLOWED_CONFIG_KEYS = {"BOT_TOKEN", "ADMIN_IDS", "WEB_ADMIN_PASSWORD"}


def _dotenv_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "'\\''") + "'"


def update_env_text(text: str, updates: dict[str, str]) -> str:
    """Replace selected dotenv values while preserving every other line."""
    validate_config_updates(updates)
    lines = text.splitlines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        key = match.group(1) if match else None
        if key in updates:
            output.append(f"{key}={_dotenv_quote(updates[key])}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={_dotenv_quote(value)}")
    return "\n".join(output).rstrip("\n") + "\n"


def validate_config_updates(updates: dict[str, str]) -> dict[str, str]:
    unknown = set(updates) - ALLOWED_CONFIG_KEYS
    if unknown:
        raise ValueError("unsupported configuration key")
    result = {key: str(value) for key, value in updates.items()}
    if "BOT_TOKEN" in result:
        token = result["BOT_TOKEN"].strip()
        if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{20,}", token):
            raise ValueError("invalid BOT_TOKEN format")
        result["BOT_TOKEN"] = token
    if "ADMIN_IDS" in result:
        ids = result["ADMIN_IDS"].strip()
        if not re.fullmatch(r"\d+(,\d+)*", ids):
            raise ValueError("invalid ADMIN_IDS format")
        result["ADMIN_IDS"] = ids
    if "WEB_ADMIN_PASSWORD" in result and not result["WEB_ADMIN_PASSWORD"]:
        raise ValueError("empty web password")
    return result


def build_service_command(service: str, action: str) -> list[str]:
    if service not in SERVICE_NAMES or action not in ALLOWED_ACTIONS:
        raise ValueError("unsupported service action")
    if action == "remove" and service != "bot":
        raise ValueError("only bot can be removed")
    if action == "status":
        return ["sudo", "-n", "/usr/local/sbin/aval-bot-admin", service, action]
    return ["sudo", "-n", "/usr/local/sbin/aval-bot-admin", service, action]


def update_env_file(path: str | Path, updates: dict[str, str]) -> None:
    """Atomically update the installer dotenv file without exposing values."""
    target = Path(path)
    new_text = update_env_text(target.read_text(encoding="utf-8"), updates)
    tmp_path = target.with_name(target.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(new_text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, target)
    target.chmod(0o600)
