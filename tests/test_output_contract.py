from __future__ import annotations

import json

from mingolf_cli.output import print_error


def test_error_contract_has_stable_keys(capsys) -> None:
    print_error(
        "Authentication required",
        "auth_required",
        {"path": "/login/api/profile"},
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["error"] == "Authentication required"
    assert payload["code"] == "auth_required"
    assert payload["details"]["path"] == "/login/api/profile"
