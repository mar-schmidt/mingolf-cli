from __future__ import annotations

import json
from pathlib import Path


def test_swedish_login_error_fixture() -> None:
    path = Path("tests/fixtures/login_error_sv.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, str)
    assert "lösenord" in value


def test_validate_error_fixture() -> None:
    path = Path("tests/fixtures/validate_errors.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["errors"]
