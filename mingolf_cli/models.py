"""Type helpers for API payloads."""

from __future__ import annotations

from typing import TypedDict


class SlotSummary(TypedDict, total=False):
    slotId: str
    timeUtc: str
    isLocked: bool
    bookable: bool
    availableSlots: int
    numbersOfSlotBookings: int
