from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mingolf_cli import exit_codes
from mingolf_cli.client import auth as auth_module
from mingolf_cli.client.auth import (
    AuthState,
    load_auth_state,
    reauthenticate,
    request_with_reauth,
    save_auth_state,
)
from mingolf_cli.config import AppPaths
from mingolf_cli.errors import CliError


class _FakeClient:
    """Stand-in for MingolfHttpClient that scripts responses per call."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, str]] = []
        self.cookies: dict[str, str] = {}

    def request_json(self, method: str, path: str, **_kwargs: Any) -> Any:
        self.calls.append((method, path))
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def cookies_dict(self) -> dict[str, str]:
        return dict(self.cookies)


def _paths(tmp_path: Path) -> AppPaths:
    return AppPaths(auth_state_path=tmp_path / "auth_state.json")


def _seed_state(paths: AppPaths, *, golf_id: str = "880628-014") -> None:
    save_auth_state(paths, AuthState(golf_id=golf_id, cookies={"mgat": "stale"}))


def _auth_required(path: str) -> CliError:
    return CliError(
        error="Authentication required",
        code="auth_required",
        exit_code=exit_codes.AUTH,
        details={"status": 401, "path": path},
    )


def test_request_with_reauth_passes_through_on_success(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    _seed_state(paths)
    client = _FakeClient([{"ok": True}])

    def fail_login(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("should not need to re-login when call succeeds")

    monkeypatch.setattr(
        "mingolf_cli.client.auth.login_with_credentials",
        fail_login,
    )

    result = request_with_reauth(client, paths, "GET", "/start/api/x")
    assert result == {"ok": True}
    assert client.calls == [("GET", "/start/api/x")]


def test_request_with_reauth_self_heals_single_401(tmp_path, monkeypatch) -> None:
    """Mirrors the bookings_list bug: /login/api/profile passed, but the
    /start/api/* call still 401s once. A forced re-login + single retry
    should succeed transparently, with no manual retry needed by the caller.
    """
    paths = _paths(tmp_path)
    _seed_state(paths)
    client = _FakeClient(
        [
            _auth_required("/start/api/Persons/HomeOverview"),
            {"golfCalender": {"futureRounds": []}},
        ]
    )
    monkeypatch.setattr(
        "mingolf_cli.client.auth.load_password",
        lambda: "hunter2",
    )
    monkeypatch.setattr(
        "mingolf_cli.client.auth.login_with_credentials",
        lambda _client, *, golf_id, password: {"personId": "p1"},
    )

    result = request_with_reauth(
        client,
        paths,
        "GET",
        "/start/api/Persons/HomeOverview",
    )

    assert result == {"golfCalender": {"futureRounds": []}}
    assert client.calls == [
        ("GET", "/start/api/Persons/HomeOverview"),
        ("GET", "/start/api/Persons/HomeOverview"),
    ]
    # Session persisted after the forced re-login.
    reloaded = load_auth_state(paths)
    assert reloaded.golf_id == "880628-014"


def test_request_with_reauth_does_not_swallow_non_auth_errors(
    tmp_path, monkeypatch
) -> None:
    paths = _paths(tmp_path)
    _seed_state(paths)
    client = _FakeClient(
        [
            CliError(
                error="Upstream API returned an error",
                code="upstream_error",
                exit_code=exit_codes.UPSTREAM,
                details={"status": 500, "path": "/start/api/x"},
            )
        ]
    )
    monkeypatch.setattr(
        "mingolf_cli.client.auth.login_with_credentials",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not re-login on a non-auth error")
        ),
    )

    with pytest.raises(CliError) as excinfo:
        request_with_reauth(client, paths, "GET", "/start/api/x")
    assert excinfo.value.code == "upstream_error"
    assert client.calls == [("GET", "/start/api/x")]


def test_request_with_reauth_propagates_failure_after_all_retries(
    tmp_path, monkeypatch
) -> None:
    """If the endpoint still 401s after every forced re-login, surface the
    error instead of retrying forever.

    One initial call plus one attempt per entry in _REAUTH_BACKOFF_SECONDS.
    """
    paths = _paths(tmp_path)
    _seed_state(paths)
    attempts = 1 + len(auth_module._REAUTH_BACKOFF_SECONDS)
    client = _FakeClient([_auth_required("/start/api/x") for _ in range(attempts)])
    monkeypatch.setattr("mingolf_cli.client.auth.time.sleep", lambda _s: None)
    monkeypatch.setattr(
        "mingolf_cli.client.auth.load_password",
        lambda: "hunter2",
    )
    monkeypatch.setattr(
        "mingolf_cli.client.auth.login_with_credentials",
        lambda _client, *, golf_id, password: {"personId": "p1"},
    )

    with pytest.raises(CliError) as excinfo:
        request_with_reauth(client, paths, "GET", "/start/api/x")
    assert excinfo.value.code == "auth_required"
    assert len(client.calls) == attempts


def test_request_with_reauth_self_heals_on_later_retry(tmp_path, monkeypatch) -> None:
    """The 2026-08-27/28/29 failure: the forced re-login AND its first retry
    both 401, and only a later, spaced attempt succeeds. Before the backoff
    fix this exited auth_required and the caller lost the data — on 08-29 that
    would have silently dropped a real tee-time booking from the sync.
    """
    paths = _paths(tmp_path)
    _seed_state(paths)
    client = _FakeClient(
        [
            _auth_required("/start/api/Persons/HomeOverview"),
            _auth_required("/start/api/Persons/HomeOverview"),
            {"ok": True, "futureRounds": [], "count": 0},
        ]
    )
    slept: list[float] = []
    monkeypatch.setattr(
        "mingolf_cli.client.auth.time.sleep", lambda s: slept.append(s)
    )
    monkeypatch.setattr("mingolf_cli.client.auth.load_password", lambda: "hunter2")
    monkeypatch.setattr(
        "mingolf_cli.client.auth.login_with_credentials",
        lambda _client, *, golf_id, password: {"personId": "p1"},
    )

    result = request_with_reauth(
        client, paths, "GET", "/start/api/Persons/HomeOverview"
    )
    assert result == {"ok": True, "futureRounds": [], "count": 0}
    assert len(client.calls) == 3
    # The recovering attempt was spaced, not fired back-to-back.
    assert slept == [auth_module._REAUTH_BACKOFF_SECONDS[1]]


def test_reauthenticate_requires_stored_golf_id(tmp_path) -> None:
    paths = _paths(tmp_path)
    save_auth_state(paths, AuthState(golf_id=None, cookies={}))
    client = _FakeClient([])

    with pytest.raises(CliError) as excinfo:
        reauthenticate(client, paths)
    assert excinfo.value.code == "missing_stored_golf_id"
