"""HTTP client wrapper for mingolf API."""

from __future__ import annotations

from typing import Any

import httpx

from mingolf_cli import exit_codes
from mingolf_cli.errors import CliError

BASE_URL = "https://mingolf.golf.se"


class MingolfHttpClient:
    """Small wrapper around httpx with consistent error mapping."""

    def __init__(
        self,
        cookies: dict[str, str] | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=timeout_seconds,
            headers={"Accept": "application/json"},
            cookies=cookies or {},
        )

    def close(self) -> None:
        self._client.close()

    def cookies_dict(self) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for cookie in self._client.cookies.jar:
            # Same cookie name can exist for different path/domain.
            cookies[cookie.name] = cookie.value
        return cookies

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: Any = None,
        allow_204: bool = False,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise CliError(
                error="Network timeout",
                code="network_timeout",
                exit_code=exit_codes.NETWORK,
                details={"path": path},
            ) from exc
        except httpx.RequestError as exc:
            raise CliError(
                error="Network request failed",
                code="network_error",
                exit_code=exit_codes.NETWORK,
                details={"path": path, "reason": str(exc)},
            ) from exc

        if response.status_code in (401, 403):
            raise CliError(
                error="Authentication required",
                code="auth_required",
                exit_code=exit_codes.AUTH,
                details={"status": response.status_code, "path": path},
            )

        if response.status_code == 204 and allow_204:
            return None

        if response.status_code >= 400:
            data: Any
            try:
                data = response.json()
            except ValueError:
                data = response.text
            raise CliError(
                error="Upstream API returned an error",
                code="upstream_error",
                exit_code=exit_codes.UPSTREAM,
                details={
                    "status": response.status_code,
                    "path": path,
                    "response": data,
                },
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise CliError(
                error="Invalid upstream JSON response",
                code="invalid_json",
                exit_code=exit_codes.UPSTREAM,
                details={"path": path, "status": response.status_code},
            ) from exc

    def request_no_content(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: Any = None,
    ) -> None:
        _ = self.request_json(
            method,
            path,
            params=params,
            payload=payload,
            allow_204=True,
        )
