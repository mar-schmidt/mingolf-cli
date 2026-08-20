"""Authentication and persisted auth_state handling."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import keyring
import keyring.errors

from mingolf_cli import exit_codes
from mingolf_cli.config import AppPaths
from mingolf_cli.errors import CliError
from mingolf_cli.client.http import MingolfHttpClient

KEYRING_SERVICE = "mingolf-cli"
KEYRING_USERNAME = "credentials"


@dataclass(slots=True)
class AuthState:
    """Persisted auth state for headless command execution."""

    golf_id: str | None = None
    cookies: dict[str, str] | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuthState":
        return cls(
            golf_id=value.get("golf_id"),
            cookies=value.get("cookies") or {},
            updated_at=value.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cookies"] = self.cookies or {}
        return data


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_auth_state(paths: AppPaths) -> AuthState:
    """Load auth state from disk, defaulting to empty."""
    path = paths.auth_state_path
    if not path.exists():
        return AuthState(cookies={})

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CliError(
            error="Failed to read auth state",
            code="auth_state_read_failed",
            exit_code=exit_codes.AUTH,
            details={"path": str(path), "reason": str(exc)},
        ) from exc
    return AuthState.from_dict(raw)


def save_auth_state(paths: AppPaths, state: AuthState) -> None:
    """Persist auth state with strict permissions."""
    path = paths.auth_state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = state.to_dict()
    data["updated_at"] = _now_iso()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.chmod(path, 0o600)


def clear_auth_state(paths: AppPaths) -> None:
    """Remove local auth state file if present."""
    path = paths.auth_state_path
    if path.exists():
        path.unlink()


def store_password(password: str) -> None:
    """Store password securely in keyring."""
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)
    except keyring.errors.KeyringError as exc:
        raise CliError(
            error="Failed to store password in keyring",
            code="keyring_store_failed",
            exit_code=exit_codes.AUTH,
            details={"reason": str(exc)},
        ) from exc


def load_password() -> str | None:
    """Load saved password from keyring."""
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except keyring.errors.KeyringError as exc:
        raise CliError(
            error="Failed to read password from keyring",
            code="keyring_read_failed",
            exit_code=exit_codes.AUTH,
            details={"reason": str(exc)},
        ) from exc


def clear_password() -> None:
    """Delete saved password from keyring when possible."""
    try:
        current = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if current is None:
            return
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except keyring.errors.KeyringError:
        return


def login_with_credentials(
    client: MingolfHttpClient,
    *,
    golf_id: str,
    password: str,
) -> dict[str, Any]:
    """Perform login and return profile."""
    profile = client.request_json(
        "POST",
        "/login/api/Users/Login",
        payload={"golfId": golf_id, "password": password},
    )
    if not isinstance(profile, dict):
        raise CliError(
            error="Unexpected login response",
            code="invalid_login_response",
            exit_code=exit_codes.UPSTREAM,
            details={"response_type": str(type(profile))},
        )
    return profile


def _relogin(
    client: MingolfHttpClient,
    paths: AppPaths,
    state: AuthState,
    *,
    require_tty_prompt: bool = False,
    checked_path: str = "/login/api/profile",
) -> dict[str, Any]:
    """Force a fresh login from stored credentials and persist the result.

    Unlike `ensure_authenticated`, this performs no cheap pre-check first —
    callers use it when they already know the cached session is stale.
    """
    if require_tty_prompt:
        raise CliError(
            error="Login required",
            code="login_required",
            exit_code=exit_codes.AUTH,
            details={"path": checked_path},
        )

    if not state.golf_id:
        raise CliError(
            error="No stored golf id for re-login",
            code="missing_stored_golf_id",
            exit_code=exit_codes.AUTH,
            details={"auth_state_path": str(paths.auth_state_path)},
        )

    password = load_password()
    if not password:
        raise CliError(
            error="No stored password for re-login",
            code="missing_stored_password",
            exit_code=exit_codes.AUTH,
            details={"hint": "Run `mingolf auth login` in a TTY first."},
        )

    profile = login_with_credentials(
        client,
        golf_id=state.golf_id,
        password=password,
    )
    state.cookies = client.cookies_dict()
    save_auth_state(paths, state)
    return profile


def ensure_authenticated(
    client: MingolfHttpClient,
    paths: AppPaths,
    *,
    require_tty_prompt: bool = False,
) -> tuple[AuthState, dict[str, Any]]:
    """Ensure a valid session, re-login from stored credentials if needed.

    Note: this only proves the session is valid against `/login/api/profile`.
    Some endpoints (e.g. `/start/api/*`) appear to be backed by a session
    store that doesn't always agree with `/login/api/profile` at the same
    instant, so passing this check is not a guarantee that every endpoint
    will accept the session too. Callers hitting those endpoints should use
    `request_with_reauth` to self-heal on a stray 401/403 instead of trusting
    this check alone.
    """
    state = load_auth_state(paths)

    try:
        profile = client.request_json("GET", "/login/api/profile")
        return state, profile
    except CliError as exc:
        if exc.exit_code != exit_codes.AUTH:
            raise

    profile = _relogin(client, paths, state, require_tty_prompt=require_tty_prompt)
    return state, profile


def reauthenticate(client: MingolfHttpClient, paths: AppPaths) -> AuthState:
    """Force a fresh login, bypassing the cached-session check entirely.

    Used by `request_with_reauth` when an endpoint reports auth_required
    despite `ensure_authenticated` having just passed, so the cached session
    must be treated as stale rather than trusted.
    """
    state = load_auth_state(paths)
    _relogin(state=state, client=client, paths=paths)
    return state


def request_with_reauth(
    client: MingolfHttpClient,
    paths: AppPaths,
    method: str,
    path: str,
    **kwargs: Any,
) -> Any:
    """Call `client.request_json`, self-healing a stray auth_required.

    Some endpoints (observed on `/start/api/*`) can 401 even immediately
    after `ensure_authenticated` confirmed the session against
    `/login/api/profile` — the two appear to be backed by different session
    stores that don't always agree at the same instant. Rather than let that
    kill the whole command, force a fresh login and retry the request once.
    """
    try:
        return client.request_json(method, path, **kwargs)
    except CliError as exc:
        if exc.code != "auth_required":
            raise
        reauthenticate(client, paths)
        return client.request_json(method, path, **kwargs)
