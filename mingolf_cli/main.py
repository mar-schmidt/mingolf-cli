"""CLI entrypoint."""

from __future__ import annotations

import typer

from mingolf_cli.client.auth import load_auth_state
from mingolf_cli.client.http import MingolfHttpClient
from mingolf_cli.commands.auth import app as auth_app
from mingolf_cli.commands.booking import app as root_app
from mingolf_cli.commands.profile import app as profile_app
from mingolf_cli.config import get_app_paths
from mingolf_cli.runtime import Runtime

app = root_app
app.pretty_exceptions_enable = False
app.add_typer(auth_app, name="auth")
app.add_typer(profile_app, name="profile")


@app.callback()
def main(
    ctx: typer.Context,
    output_format: str = typer.Option("json", "--format"),
) -> None:
    """Initialize runtime objects for each command invocation."""
    if output_format not in {"json", "text"}:
        raise typer.BadParameter("format must be one of: json, text")
    paths = get_app_paths()
    state = load_auth_state(paths)
    client = MingolfHttpClient(cookies=state.cookies or {})
    ctx.obj = Runtime(
        paths=paths,
        state=state,
        client=client,
        output_format=output_format,
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
