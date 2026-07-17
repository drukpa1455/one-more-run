"""User-owned credentials for One More Run."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path


NAMES = ("CODEX_API_KEY", "AKASH_API_KEY")


def path() -> Path:
    configured = os.environ.get("OMR_CREDENTIALS")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "one-more-run" / "credentials.json"


def secret(name: str) -> str | None:
    """Read a credential, preferring a process-scoped override."""
    value = os.environ.get(name)
    if value:
        return value
    return load().get(name)


def load(location: Path | None = None) -> dict[str, str]:
    location = location or path()
    if not location.exists():
        return {}
    if os.name != "nt" and location.stat().st_mode & 0o077:
        raise ValueError(f"credentials must not be group/world accessible: {location}")
    try:
        value = json.loads(location.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid credentials file: {location}") from error
    if not isinstance(value, dict):
        raise ValueError(f"credentials must be a JSON object: {location}")
    credentials: dict[str, str] = {}
    for name, item in value.items():
        if name not in NAMES or not isinstance(item, str) or not item:
            raise ValueError(f"invalid credential {name!r}: {location}")
        credentials[name] = item
    return credentials


def configure(from_environment: bool = False) -> Path:
    """Collect credentials without placing secrets in shell history."""
    location = path()
    credentials = load(location)
    if from_environment:
        supplied = {name: os.environ[name] for name in NAMES if os.environ.get(name)}
        if not supplied:
            raise ValueError(
                "set CODEX_API_KEY or AKASH_API_KEY before using --from-env"
            )
        credentials.update(supplied)
    else:
        prompts = {
            "CODEX_API_KEY": "Codex API key (optional when `codex login` is active)",
            "AKASH_API_KEY": "Akash Console API key",
        }
        for name in NAMES:
            suffix = " [keep existing]" if name in credentials else ""
            value = getpass.getpass(f"{prompts[name]}{suffix}: ").strip()
            if value:
                credentials[name] = value
    if not credentials:
        raise ValueError("no credentials supplied")
    save(credentials, location)
    return location


def save(credentials: dict[str, str], location: Path | None = None) -> None:
    location = location or path()
    location.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        location.parent.chmod(0o700)
    temporary = location.with_name(f".{location.name}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump(credentials, output, sort_keys=True)
            output.write("\n")
        os.replace(temporary, location)
        if os.name != "nt":
            location.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)
