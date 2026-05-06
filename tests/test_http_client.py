from __future__ import annotations

from mingolf_cli.client.http import MingolfHttpClient


def test_cookies_dict_handles_duplicate_cookie_names() -> None:
    client = MingolfHttpClient()
    try:
        client._client.cookies.set("mgat", "v1", domain="mingolf.golf.se")
        client._client.cookies.set(
            "mgat",
            "v2",
            domain="mingolf.golf.se",
            path="/bokning",
        )
        value = client.cookies_dict()
        assert value["mgat"] in {"v1", "v2"}
    finally:
        client.close()
