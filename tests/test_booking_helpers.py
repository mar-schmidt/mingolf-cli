from __future__ import annotations

import re

from mingolf_cli.client.booking import BookingPlayer, generate_slot_booking_id


def test_slot_booking_id_format() -> None:
    value = generate_slot_booking_id()
    assert re.match(r"^new_\d{13}_[a-z]{8}$", value)


def test_booking_player_payload() -> None:
    player = BookingPlayer(
        person_id="person",
        golf_id="123",
        first_name="Ada",
        last_name="Lovelace",
        gender="Female",
        age=36,
        hcp="6,6",
        home_club="Example Club",
    )
    payload = player.as_payload()
    assert payload["fullName"] == "Ada Lovelace"
    assert payload["hashId"] == "person"
    assert payload["isBooker"] is True
