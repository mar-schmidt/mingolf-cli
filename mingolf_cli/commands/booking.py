"""Booking and tee-time commands."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import typer

from mingolf_cli import exit_codes
from mingolf_cli.client.auth import ensure_authenticated, save_auth_state
from mingolf_cli.client.booking import (
    BookingPlayer,
    cancel_booking as cancel_booking_api,
    create_booking,
    generate_slot_booking_id,
    get_course_schedule,
    get_playing_handicaps,
    list_club_courses,
    list_clubs,
    lock_slot,
    unlock_slot,
    validate_booking,
)
from mingolf_cli.cli_common import run_json
from mingolf_cli.config import get_default_club_id, get_default_course_id
from mingolf_cli.errors import CliError
from mingolf_cli.runtime import get_runtime

app = typer.Typer(help="Booking commands.")
bookings_app = typer.Typer(help="Manage your bookings.")
app.add_typer(bookings_app, name="bookings")


def _resolve_club_id(club: str | None) -> str:
    if club:
        return club
    from_env = get_default_club_id()
    if from_env:
        return from_env
    raise CliError(
        error="Missing club id",
        code="missing_club_id",
        exit_code=exit_codes.USAGE,
        details={"hint": "Provide --club or set MINGOLF_CLUB_ID"},
    )


def _resolve_course_id(course: str | None) -> str:
    if course:
        return course
    from_env = get_default_course_id()
    if from_env:
        return from_env
    raise CliError(
        error="Missing course id",
        code="missing_course_id",
        exit_code=exit_codes.USAGE,
        details={"hint": "Provide --course or set MINGOLF_COURSE_ID"},
    )


def _validate_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise CliError(
            error="Invalid date format",
            code="invalid_date",
            exit_code=exit_codes.USAGE,
            details={"expected": "YYYY-MM-DD", "value": value},
        ) from exc


@app.command("clubs")
def clubs(
    ctx: typer.Context,
    search: str | None = typer.Option(None, "--search"),
) -> None:
    """List available golf clubs."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        clubs_data = list_clubs(runtime.client)
        if search:
            lowered = search.lower()
            clubs_data = [
                item
                for item in clubs_data
                if lowered in str(item.get("name", "")).lower()
            ]
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {"ok": True, "clubs": clubs_data, "count": len(clubs_data)}

    run_json(action)


@app.command("courses")
def courses(
    ctx: typer.Context,
    club: str | None = typer.Option(None, "--club"),
    search: str | None = typer.Option(None, "--search"),
) -> None:
    """List courses for a club id."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        resolved_club = _resolve_club_id(club)
        courses_data = list_club_courses(
            runtime.client,
            club_id=resolved_club,
        )
        if search:
            lowered = search.lower()
            courses_data = [
                item
                for item in courses_data
                if lowered in str(item.get("name", "")).lower()
            ]
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {
            "ok": True,
            "clubId": resolved_club,
            "courses": courses_data,
            "count": len(courses_data),
        }

    run_json(action)


@app.command("tee-times")
def tee_times(
    ctx: typer.Context,
    course: str | None = typer.Option(None, "--course"),
    date: str = typer.Option(..., "--date"),
    club: str | None = typer.Option(None, "--club"),
) -> None:
    """List tee times, each with slotId for bookings create."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        _validate_date(date)
        resolved_club = _resolve_club_id(club)
        resolved_course = _resolve_course_id(course)
        schedule = get_course_schedule(
            runtime.client,
            club_id=resolved_club,
            course_id=resolved_course,
            date=date,
        )
        slots = schedule.get("slots") or []
        mapped = []
        for slot in slots:
            availability = slot.get("availablity") or {}
            mapped.append(
                {
                    "slotId": slot.get("id"),
                    "timeUtc": slot.get("time"),
                    "isLocked": slot.get("isLocked"),
                    "bookable": availability.get("bookable"),
                    "availableSlots": availability.get("availableSlots"),
                    "numbersOfSlotBookings": availability.get(
                        "numbersOfSlotBookings"
                    ),
                }
            )
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {
            "ok": True,
            "clubId": resolved_club,
            "courseId": resolved_course,
            "date": date,
            "slots": mapped,
            "count": len(mapped),
        }

    run_json(action)


@bookings_app.command("list")
def bookings_list(ctx: typer.Context) -> None:
    """List future rounds from HomeOverview."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        home = runtime.client.request_json(
            "GET",
            "/start/api/Persons/HomeOverview",
        )
        calendar = home.get("golfCalender") or {}
        rounds = calendar.get("futureRounds") or []
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {"ok": True, "futureRounds": rounds, "count": len(rounds)}

    run_json(action)


def _player_from_profile(profile: dict[str, Any]) -> BookingPlayer:
    return BookingPlayer(
        person_id=str(profile.get("personId")),
        golf_id=str(profile.get("golfId")),
        first_name=str(profile.get("firstName")),
        last_name=str(profile.get("lastName")),
        gender=str(profile.get("gender")),
        age=int(profile.get("age") or 0),
        hcp=str(profile.get("hcp")),
        home_club=str(profile.get("homeClubName")),
    )


def _build_payload(
    player: BookingPlayer,
    slot_booking_id: str,
) -> dict[str, Any]:
    return {
        "slotBookingId": slot_booking_id,
        "createdNumber": 1,
        "state": "Added",
        "hasArrived": False,
        "hasBeenValidated": False,
        "isNineHole": False,
        "player": player.as_payload(),
    }


@bookings_app.command("create")
def bookings_create(
    ctx: typer.Context,
    slot: str = typer.Option(..., "--slot"),
    tee: str | None = typer.Option(None, "--tee"),
) -> None:
    """Create a booking from a slot id."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        _, profile = ensure_authenticated(runtime.client, runtime.paths)

        player = _player_from_profile(profile)
        slot_booking_id = generate_slot_booking_id()
        entry = _build_payload(player, slot_booking_id)
        payload = [entry]
        slot_locked = False
        try:
            lock_slot(runtime.client, slot)
            slot_locked = True

            validation = validate_booking(
                runtime.client,
                slot_id=slot,
                payload=payload,
            )
            errors = validation.get("errors") or []
            if errors:
                raise CliError(
                    error="Booking validation failed",
                    code="booking_validation_failed",
                    exit_code=exit_codes.USAGE,
                    details={"slotId": slot, "errors": errors},
                )

            payload[0]["hasBeenValidated"] = True
            handicap_data = get_playing_handicaps(
                runtime.client,
                slot_id=slot,
                payload=payload,
            )
            if not handicap_data:
                raise CliError(
                    error="Missing tee options",
                    code="missing_tee_options",
                    exit_code=exit_codes.UPSTREAM,
                    details={"slotId": slot},
                )

            tees = handicap_data[0].get("tees") or []
            selected = None
            if tee:
                for candidate in tees:
                    if tee in (
                        candidate.get("teeId"),
                        candidate.get("teeName"),
                    ):
                        selected = candidate
                        break
            if selected is None:
                for candidate in tees:
                    if candidate.get("isDefault"):
                        selected = candidate
                        break
            if selected is None and tees:
                selected = tees[0]
            if selected is None:
                raise CliError(
                    error="No usable tee found",
                    code="no_usable_tee",
                    exit_code=exit_codes.USAGE,
                    details={"slotId": slot, "requestedTee": tee},
                )

            payload[0]["player"]["tee"] = {
                "teeId": selected.get("teeId"),
                "teeName": selected.get("teeName"),
                "playingHandicap": selected.get("playingHandicap"),
                "saveAsDefault": False,
            }
            created = create_booking(
                runtime.client,
                slot_id=slot,
                payload=payload,
            )
            runtime.state.cookies = runtime.client.cookies_dict()
            save_auth_state(runtime.paths, runtime.state)
            return {
                "ok": True,
                "slotId": slot,
                "slotBookingId": slot_booking_id,
                "selectedTee": payload[0]["player"]["tee"],
                "bookings": created,
            }
        except Exception:
            if slot_locked:
                try:
                    unlock_slot(runtime.client, slot)
                except Exception:
                    pass
            raise

    run_json(action)


@bookings_app.command("cancel")
def bookings_cancel(
    ctx: typer.Context,
    booking: str = typer.Option(..., "--booking"),
) -> None:
    """Cancel an existing booking by booking id."""

    def action() -> dict[str, Any]:
        runtime = get_runtime(ctx)
        ensure_authenticated(runtime.client, runtime.paths)
        cancel_booking_api(runtime.client, booking)
        runtime.state.cookies = runtime.client.cookies_dict()
        save_auth_state(runtime.paths, runtime.state)
        return {"ok": True, "bookingId": booking, "cancelled": True}

    run_json(action)
