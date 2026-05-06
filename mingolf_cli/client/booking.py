"""Booking-specific API helpers."""

from __future__ import annotations

import random
import string
import time
from dataclasses import dataclass
from typing import Any

from mingolf_cli.client.http import MingolfHttpClient


@dataclass(slots=True)
class BookingPlayer:
    """Player fields required by booking endpoints."""

    person_id: str
    golf_id: str
    first_name: str
    last_name: str
    gender: str
    age: int
    hcp: str
    home_club: str
    is_booker: bool = True
    is_guest: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def as_payload(self) -> dict[str, Any]:
        return {
            "personId": self.person_id,
            "hashId": self.person_id,
            "golfId": self.golf_id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "fullName": self.full_name,
            "gender": self.gender,
            "age": self.age,
            "hcp": self.hcp,
            "homeClub": self.home_club,
            "isBooker": self.is_booker,
            "isGuest": self.is_guest,
        }


def generate_slot_booking_id() -> str:
    """Generate API-compatible temporary slot booking id."""
    suffix = "".join(random.choices(string.ascii_lowercase, k=8))
    millis = int(time.time() * 1000)
    return f"new_{millis}_{suffix}"


def list_clubs(client: MingolfHttpClient) -> list[dict[str, Any]]:
    data = client.request_json("GET", "/bokning/api/Clubs")
    return data if isinstance(data, list) else []


def get_course_schedule(
    client: MingolfHttpClient,
    *,
    club_id: str,
    course_id: str,
    date: str,
) -> dict[str, Any]:
    data = client.request_json(
        "GET",
        f"/bokning/api/Clubs/{club_id}/CourseSchedule",
        params={"courseId": course_id, "date": date},
    )
    return data if isinstance(data, dict) else {}


def list_club_courses(
    client: MingolfHttpClient,
    *,
    club_id: str,
) -> list[dict[str, Any]]:
    """Return courses for a specific club id."""
    data = client.request_json("GET", "/hcp/api/Clubs/Courses")
    if not isinstance(data, list):
        return []
    for club in data:
        if club.get("id") != club_id:
            continue
        courses = club.get("courses") or []
        if not isinstance(courses, list):
            return []
        return courses
    return []


def lock_slot(client: MingolfHttpClient, slot_id: str) -> Any:
    return client.request_json("POST", f"/bokning/api/Slot/{slot_id}/Lock")


def unlock_slot(client: MingolfHttpClient, slot_id: str) -> None:
    client.request_no_content("DELETE", f"/bokning/api/Slot/{slot_id}/Lock")


def validate_booking(
    client: MingolfHttpClient,
    *,
    slot_id: str,
    payload: list[dict[str, Any]],
) -> dict[str, Any]:
    data = client.request_json(
        "POST",
        f"/bokning/api/Slot/{slot_id}/Bookings/Validate",
        payload=payload,
    )
    return data if isinstance(data, dict) else {}


def get_playing_handicaps(
    client: MingolfHttpClient,
    *,
    slot_id: str,
    payload: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    data = client.request_json(
        "POST",
        f"/bokning/api/Slot/{slot_id}/Players/PlayingHandicaps",
        payload=payload,
    )
    return data if isinstance(data, list) else []


def create_booking(
    client: MingolfHttpClient,
    *,
    slot_id: str,
    payload: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    data = client.request_json(
        "POST",
        f"/bokning/api/Slot/{slot_id}/Bookings",
        payload=payload,
    )
    return data if isinstance(data, list) else []


def cancel_booking(client: MingolfHttpClient, booking_id: str) -> None:
    client.request_no_content(
        "DELETE",
        f"/bokning/api/Slot/Bookings/{booking_id}",
    )
