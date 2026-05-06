"""Authentication command group."""

from __future__ import annotations

from typing import Any

import typer

from mingolf_cli.client.auth import (
    clear_auth_state,
    clear_password,
    ensure_authenticated,
    load_auth_state,
    login_with_credentials,
    save_auth_state,
    store_password,
)
from mingolf_cli.cli_common import run_json
from mingolf_cli.runtime import get_runtime

app = typer.Typer(help="Authentication commands.")


def _profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "personId": profile.get("personId"),
        "golfId": profile.get("golfId"),
        "firstName": profile.get("firstName"),
        "lastName": profile.get("lastName"),
        "homeClubName": profile.get("homeClubName"),
        "hcp": profile.get("hcp"),
    }


@app.command("login")
def login(
    ctx: typer.Context,
    golf_id: str | None = typer.Option(None, "--golf-id"),
    password: str | None = typer.Option(None, "--password"),
) -> None:
    """One-time interactive login and credential persistence."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        resolved_golf_id = golf_id or typer.prompt("Golf ID")
        resolved_password = password or typer.prompt(
            "Password",
            hide_input=True,
        )
        profile = login_with_credentials(
            runtime.client,
            golf_id=resolved_golf_id,
            password=resolved_password,
        )
        # Login can sometimes return sparse data; fetch canonical profile.
        if not profile.get("personId"):
            profile = runtime.client.request_json("GET", "/login/api/profile")
        runtime.state.golf_id = resolved_golf_id
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        store_password(resolved_password)
        return {
            "ok": True,
            "authStatePath": str(runtime.paths.auth_state_path),
            "profile": _profile_summary(profile),
        }

    run_json(action)


@app.command("status")
def status(ctx: typer.Context) -> None:
    """Check current auth status using profile endpoint."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        _, profile = ensure_authenticated(runtime.client, runtime.paths)
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {
            "ok": True,
            "authenticated": True,
            "profile": _profile_summary(profile),
        }

    run_json(action)


@app.command("logout")
def logout(
    ctx: typer.Context,
    forget_creds: bool = typer.Option(False, "--forget-creds"),
) -> None:
    """Logout and clear local session state."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        try:
            runtime.client.request_no_content("POST", "/login/api/logout")
        except Exception:
            pass

        clear_auth_state(runtime.paths)
        if forget_creds:
            clear_password()
        runtime.state = load_auth_state(runtime.paths)
        return {"ok": True, "forgetCreds": forget_creds}

    run_json(action)
