#!/usr/bin/env python3
"""Generate .agent/skill.json from .agent/SKILL.md frontmatter."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: PyYAML. Install with `pip install pyyaml`."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = ROOT / ".agent" / "SKILL.md"
SKILL_JSON = ROOT / ".agent" / "skill.json"
ENTRYPOINT = "mingolf"

COMMANDS = [
    "auth login",
    "auth status",
    "auth logout",
    "profile",
    "clubs",
    "courses",
    "tee-times",
    "bookings list",
    "bookings create",
    "bookings cancel",
]

REQUIRED_KEYS = ["name", "version", "description", "compatibility"]


def parse_frontmatter(markdown_text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", markdown_text, flags=re.S)
    if not match:
        raise ValueError("Could not find YAML frontmatter in SKILL.md")
    parsed = yaml.safe_load(match.group(1))
    if not isinstance(parsed, dict):
        raise ValueError("Frontmatter must parse to a YAML mapping")
    return parsed


def build_manifest(frontmatter: dict) -> dict:
    missing = [key for key in REQUIRED_KEYS if key not in frontmatter]
    if missing:
        raise ValueError(f"Missing required frontmatter keys: {missing}")

    manifest = {
        "name": frontmatter["name"],
        "version": str(frontmatter["version"]),
        "schemaVersion": "1",
        "description": frontmatter["description"],
        "source": (
            "https://raw.githubusercontent.com/marcus/mingolf-cli/main/"
            ".agent/SKILL.md"
        ),
        "install": frontmatter.get("install", {}),
        "entrypoint": ENTRYPOINT,
        "commands": COMMANDS,
        "compatibility": frontmatter["compatibility"],
    }
    return manifest


def main() -> int:
    if not SKILL_MD.exists():
        raise FileNotFoundError(f"Missing skill file: {SKILL_MD}")

    frontmatter = parse_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    manifest = build_manifest(frontmatter)
    SKILL_JSON.parent.mkdir(parents=True, exist_ok=True)
    SKILL_JSON.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {SKILL_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
