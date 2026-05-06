"""Configuration helpers for filesystem paths and env defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

AUTH_STATE_ENV = "MINGOLF_CLI_AUTH_STATE_PATH"
DEFAULT_CLUB_ENV = "MINGOLF_CLUB_ID"
DEFAULT_COURSE_ENV = "MINGOLF_COURSE_ID"


@dataclass(slots=True)
class AppPaths:
    """Resolved filesystem paths used by the CLI."""

    auth_state_path: Path


def get_app_paths() -> AppPaths:
    """Resolve state file path from env or default config location."""
    from_env = os.environ.get(AUTH_STATE_ENV)
    if from_env:
        return AppPaths(auth_state_path=Path(from_env).expanduser())

    root = Path.home() / ".config" / "mingolf-cli"
    return AppPaths(auth_state_path=root / "auth_state.json")


def get_default_club_id() -> str | None:
    """Read optional default club id from env."""
    return os.environ.get(DEFAULT_CLUB_ENV)


def get_default_course_id() -> str | None:
    """Read optional default course id from env."""
    return os.environ.get(DEFAULT_COURSE_ENV)
