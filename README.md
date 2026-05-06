# mingolf-cli

JSON-first CLI for the Swedish Mingolf booking service.

`mingolf-cli` helps you authenticate, discover clubs and courses, list
available tee times, and create or cancel bookings from scripts, terminal
workflows and AI agents.

## Features

- machine-readable JSON output by default
- stable error contract (`error`, `code`, `details`)
- fixed exit codes for automation
- persisted auth state for headless usage
- environment defaults for club and course ids

## Install CLI

Primary install path:

```bash
pip install "git+https://github.com/mar-schmidt/mingolf-cli.git"
```

Verify:

```bash
mingolf --help
```

Optional convenience:

```bash
pipx install mingolf-cli
```

Local development install:

```bash
pipx install --force /path/to/mingolf-cli
```

## Quickstart

Login and verify:

```bash
mingolf auth login
mingolf auth status
```

Discover and book:

```bash
mingolf clubs --search "club name"
mingolf courses --club <clubId>
mingolf tee-times --club <clubId> --course <courseId> --date 2026-05-08
mingolf bookings create --slot <slotId>
```

List and cancel:

```bash
mingolf bookings list
mingolf bookings cancel --booking <bookingId>
```

## Environment variables

- `MINGOLF_CLI_AUTH_STATE_PATH`: override auth-state file path.
- `MINGOLF_CLUB_ID`: default value for `--club`.
- `MINGOLF_COURSE_ID`: default value for `--course`.

## Agent Skill

Primary path (recommended): install the compiled `.skill` artifact from CI.

A GitHub Actions workflow packages `dist/mingolf-cli.skill` on every push and
pull request. Download the `.skill` file from workflow artifacts and install
it in your agent platform of choice.

Secondary path: use the source skill files in `.agent/`.

Canonical skill source URLs:

- latest:
  `https://raw.githubusercontent.com/mar-schmidt/mingolf-cli/main/.agent/SKILL.md`
- pinned:
  `https://raw.githubusercontent.com/mar-schmidt/mingolf-cli/vX.Y.Z/.agent/SKILL.md`

Manual local install from source:

```bash
mkdir -p ~/.agents/skills/mingolf-cli
cp -R .agent/* ~/.agents/skills/mingolf-cli/
```

Or symlink:

```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)/.agent" ~/.agents/skills/mingolf-cli
```

## API documentation

Simplified reverse-engineered API notes:

- `docs/api.md`

## Contributing

### Setup

```bash
python3 -m pip install -e .
python3 -m pip install pytest pyyaml
```

### Validate changes

```bash
python3 -m pytest
python3 -m mingolf_cli --help
python3 scripts/generate-skill-manifest.py
python3 scripts/package-skill.py
```

### Contribution expectations

- keep JSON output and error contract stable
- update `.agent/SKILL.md` when commands or workflows change
- regenerate `.agent/skill.json` after skill frontmatter updates
- keep `docs/api.md` aligned with documented API behavior
- keep line length at or below 80 characters
