"""Profile commands."""

from __future__ import annotations

import typer

from mingolf_cli.client.auth import ensure_authenticated, save_auth_state
from mingolf_cli.cli_common import run_json
from mingolf_cli.runtime import get_runtime

app = typer.Typer(help="Profile commands.")


@app.callback(invoke_without_command=True)
def show(ctx: typer.Context) -> None:
    """Return current user profile as JSON."""

    def action() -> dict:
        runtime = get_runtime(ctx)
        _, profile = ensure_authenticated(runtime.client, runtime.paths)
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {"ok": True, "profile": profile}

    run_json(action)
