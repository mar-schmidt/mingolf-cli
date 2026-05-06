from __future__ import annotations

from mingolf_cli.config import get_default_club_id, get_default_course_id


def test_default_club_id_env(monkeypatch) -> None:
    monkeypatch.setenv("MINGOLF_CLUB_ID", "club-123")
    assert get_default_club_id() == "club-123"


def test_default_course_id_env(monkeypatch) -> None:
    monkeypatch.setenv("MINGOLF_COURSE_ID", "course-456")
    assert get_default_course_id() == "course-456"
