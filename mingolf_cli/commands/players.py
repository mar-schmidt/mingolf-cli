"""Player discovery commands."""

from __future__ import annotations

from typing import Any

import typer

from mingolf_cli.client.auth import ensure_authenticated, save_auth_state
from mingolf_cli.client.booking import search_players
from mingolf_cli.cli_common import run_json
from mingolf_cli.runtime import get_runtime

app = typer.Typer(help="Find players by golf id.")


@app.command("search")
def players_search(
    ctx: typer.Context,
    search: str = typer.Option(..., "--search"),
    country: str = typer.Option("Sweden", "--country"),
) -> None:
    """Search players that can be added to bookings."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        players = search_players(
            runtime.client,
            search_phrase=search,
            country=country,
        )
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {
            "ok": True,
            "search": search,
            "country": country,
            "players": players,
            "count": len(players),
        }

    run_json(action)
