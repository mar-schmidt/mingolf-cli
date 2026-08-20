from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from mingolf_cli import exit_codes
from mingolf_cli.client.auth import AuthState
from mingolf_cli.errors import CliError
from mingolf_cli.main import app

runner = CliRunner()


def _prepare(monkeypatch, tmp_path: Path) -> None:
    auth_state_path = tmp_path / "auth_state.json"
    monkeypatch.setenv("MINGOLF_CLI_AUTH_STATE_PATH", str(auth_state_path))
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.ensure_authenticated",
        lambda _client, _paths: (
            AuthState(cookies={}),
            {
                "personId": "person-1",
                "golfId": "880628-014",
                "firstName": "Marcus",
                "lastName": "Schmidt",
                "gender": "Male",
                "age": 38,
                "hcp": "6,6",
                "homeClubName": "Chalmers Golfklubb",
            },
        ),
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.players.ensure_authenticated",
        lambda _client, _paths: (
            AuthState(cookies={}),
            {},
        ),
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.save_auth_state",
        lambda _paths, _state: None,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.players.save_auth_state",
        lambda _paths, _state: None,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.lock_slot",
        lambda _client, _slot_id: {"ok": True},
    )


def test_bookings_create_single_player_still_works(
    monkeypatch,
    tmp_path,
) -> None:
    _prepare(monkeypatch, tmp_path)
    validate_sizes: list[int] = []
    handicap_sizes: list[int] = []
    captured_payload: list[dict[str, Any]] = []

    def fake_validate(_client, *, slot_id: str, payload: list[dict[str, Any]]):
        del slot_id
        validate_sizes.append(len(payload))
        return {"errors": []}

    def fake_handicaps(
        _client,
        *,
        slot_id: str,
        payload: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del slot_id
        handicap_sizes.append(len(payload))
        return [
            {
                "tees": [
                    {
                        "teeId": "tee-1",
                        "teeName": "Blue",
                        "playingHandicap": "11,2",
                        "isDefault": True,
                    }
                ]
            }
            for _ in payload
        ]

    def fake_create(_client, *, slot_id: str, payload: list[dict[str, Any]]):
        del slot_id
        captured_payload.extend(payload)
        return [{"bookingId": "booking-1"}]

    monkeypatch.setattr(
        "mingolf_cli.commands.booking.validate_booking",
        fake_validate,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.get_playing_handicaps",
        fake_handicaps,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.create_booking",
        fake_create,
    )

    result = runner.invoke(app, ["bookings", "create", "--slot", "slot-1"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["playerCount"] == 1
    assert len(output["slotBookingIds"]) == 1
    assert validate_sizes == [1]
    assert handicap_sizes == [1]
    assert captured_payload[0]["createdNumber"] == 1
    assert captured_payload[0]["player"]["isBooker"] is True


def test_bookings_create_with_companion(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)
    validate_sizes: list[int] = []
    handicap_sizes: list[int] = []
    captured_payload: list[dict[str, Any]] = []

    def fake_validate(_client, *, slot_id: str, payload: list[dict[str, Any]]):
        del slot_id
        validate_sizes.append(len(payload))
        return {"errors": []}

    def fake_handicaps(
        _client,
        *,
        slot_id: str,
        payload: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del slot_id
        handicap_sizes.append(len(payload))
        return [
            {
                "tees": [
                    {
                        "teeId": f"tee-{index}",
                        "teeName": "Blue",
                        "playingHandicap": "11,2",
                        "isDefault": True,
                    }
                ]
            }
            for index, _ in enumerate(payload, start=1)
        ]

    def fake_create(_client, *, slot_id: str, payload: list[dict[str, Any]]):
        del slot_id
        captured_payload.extend(payload)
        return [{"bookingId": "booking-1"}, {"bookingId": "booking-2"}]

    def fake_search(_client, *, search_phrase: str, country: str):
        assert country == "Sweden"
        return [
            {
                "personId": "person-2",
                "golfId": search_phrase,
                "firstName": "Robert",
                "lastName": "Ronelius",
                "gender": "Male",
                "age": 42,
                "hcp": "14,5",
                "homeClub": "Chalmers Golfklubb",
            }
        ]

    monkeypatch.setattr(
        "mingolf_cli.commands.booking.validate_booking",
        fake_validate,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.get_playing_handicaps",
        fake_handicaps,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.create_booking",
        fake_create,
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.search_players",
        fake_search,
    )

    result = runner.invoke(
        app,
        [
            "bookings",
            "create",
            "--slot",
            "slot-1",
            "--companion-golf-id",
            "840225-034",
        ],
    )
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["playerCount"] == 2
    assert len(output["slotBookingIds"]) == 2
    assert validate_sizes == [1, 2]
    assert handicap_sizes == [1, 2]
    assert captured_payload[1]["createdNumber"] == 2
    assert captured_payload[1]["player"]["isBooker"] is False
    assert captured_payload[1]["player"]["golfId"] == "840225-034"


def test_bookings_create_fails_when_companion_missing(
    monkeypatch,
    tmp_path,
) -> None:
    _prepare(monkeypatch, tmp_path)

    monkeypatch.setattr(
        "mingolf_cli.commands.booking.validate_booking",
        lambda _client, *, slot_id, payload: {"errors": []},
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.get_playing_handicaps",
        lambda _client, *, slot_id, payload: [
            {
                "tees": [
                    {
                        "teeId": "tee-1",
                        "teeName": "Blue",
                        "playingHandicap": "11,2",
                        "isDefault": True,
                    }
                ]
            }
        ],
    )
    monkeypatch.setattr(
        "mingolf_cli.commands.booking.search_players",
        lambda _client, *, search_phrase, country: [],
    )

    result = runner.invoke(
        app,
        [
            "bookings",
            "create",
            "--slot",
            "slot-1",
            "--companion-golf-id",
            "840225-034",
        ],
    )
    assert result.exit_code == 1
    error = json.loads(result.output)
    assert error["code"] == "player_not_found"


def test_bookings_list_maps_future_rounds(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_request_with_reauth(_client, _paths, method, path, **_kwargs):
        calls.append((method, path))
        return {
            "golfCalender": {
                "futureRounds": [{"bookingId": "b1"}, {"bookingId": "b2"}]
            }
        }

    monkeypatch.setattr(
        "mingolf_cli.commands.booking.request_with_reauth",
        fake_request_with_reauth,
    )

    result = runner.invoke(app, ["bookings", "list"])
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["ok"] is True
    assert output["count"] == 2
    assert calls == [("GET", "/start/api/Persons/HomeOverview")]


def test_bookings_list_uses_reauth_wrapper_not_raw_request(
    monkeypatch,
    tmp_path,
) -> None:
    """Regression guard for the intermittent-401 bug: `ensure_authenticated`
    only validates `/login/api/profile`, which can pass while `/start/api/*`
    still momentarily 401s (different backend/session store). `bookings_list`
    must route that call through `request_with_reauth` -- which force-relogs
    and retries once on `auth_required` -- rather than calling
    `client.request_json` directly, which has no such recovery and would
    just die (as seen repeatedly in the HA family-calendar-sync job).
    """
    _prepare(monkeypatch, tmp_path)

    def fail_if_called_directly(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(
            "bookings_list must not call client.request_json directly for "
            "/start/api/*; use request_with_reauth instead"
        )

    monkeypatch.setattr(
        "mingolf_cli.client.http.MingolfHttpClient.request_json",
        fail_if_called_directly,
    )

    calls: list[tuple[str, str]] = []

    def fake_request_with_reauth(_client, _paths, method, path, **_kwargs):
        calls.append((method, path))
        return {"golfCalender": {"futureRounds": []}}

    monkeypatch.setattr(
        "mingolf_cli.commands.booking.request_with_reauth",
        fake_request_with_reauth,
    )

    result = runner.invoke(app, ["bookings", "list"])
    assert result.exit_code == 0
    assert calls == [("GET", "/start/api/Persons/HomeOverview")]


def test_players_search_command(monkeypatch, tmp_path) -> None:
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "mingolf_cli.commands.players.search_players",
        lambda _client, *, search_phrase, country: [
            {
                "golfId": search_phrase,
                "name": "Robert Ronelius",
                "country": country,
            }
        ],
    )
    result = runner.invoke(
        app,
        ["players", "search", "--search", "840225-034"],
    )
    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["ok"] is True
    assert output["country"] == "Sweden"
    assert output["count"] == 1
