"""Runtime context shared by commands."""

from __future__ import annotations

from dataclasses import dataclass

import typer

from mingolf_cli.client.auth import AuthState
from mingolf_cli.client.http import MingolfHttpClient
from mingolf_cli.config import AppPaths


@dataclass(slots=True)
class Runtime:
    """Objects used by command handlers."""

    paths: AppPaths
    client: MingolfHttpClient
    state: AuthState
    output_format: str = "json"


def get_runtime(ctx: typer.Context) -> Runtime:
    value = ctx.obj
    if not isinstance(value, Runtime):
        raise RuntimeError("Runtime is not initialized")
    return value
