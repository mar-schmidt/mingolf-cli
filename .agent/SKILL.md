---
name: mingolf-cli
version: 1.0.0
description: >
  Use the Mingolf CLI to authenticate and manage Swedish golf tee times.
  Trigger this skill when the user mentions mingolf, golf bookings, tee-times,
  slotId, courseId, clubId, or start-time scheduling workflows.
author: mar-schmidt
repo: https://github.com/mar-schmidt/mingolf-cli
install:
  pip: pip install "git+https://github.com/mar-schmidt/mingolf-cli.git"
  pipx: pipx install "git+https://github.com/mar-schmidt/mingolf-cli.git"
requires:
  - python: ">=3.11"
compatibility:
  - claude-desktop
  - cursor
  - continue
  - generic-mcp
tags:
  - golf
  - bookings
  - cli
  - mingolf
---

# Skill: mingolf-cli

## When to use

Use this skill when a user wants to:

- log into Mingolf from terminal workflows
- find clubs, courses, and available start times
- book or cancel a tee time
- chain machine-readable command output between steps

## What this CLI does

`mingolf` is a JSON-first CLI for `mingolf.golf.se`. It persists login state
for headless usage and supports booking workflows from discovery to create and
cancel.

## Installation

```bash
pip install "git+https://github.com/mar-schmidt/mingolf-cli.git"
mingolf --help
```

Optional:

```bash
pipx install "git+https://github.com/mar-schmidt/mingolf-cli.git"
mingolf --help
```

## Core concepts

- **Club**: golf club, identified by `clubId` UUID.
- **Course**: course within a club, identified by `courseId` UUID.
- **Slot**: tee-time entry, identified by `slotId` UUID.
- **Booking**: created reservation, identified by `bookingId` UUID.
- **Slot booking id**: temporary id generated during booking payload creation.

## Output and errors

- Default output is JSON (`--format json`).
- Text mode exists for human readability (`--format text`).
- Error payload format is stable:
  - `error`
  - `code`
  - `details`
- Exit codes:
  - `0` success
  - `1` usage/validation
  - `2` auth
  - `3` upstream API
  - `4` network

## Environment defaults

- `MINGOLF_CLI_AUTH_STATE_PATH`: custom auth-state file path.
- `MINGOLF_CLUB_ID`: default `--club` value.
- `MINGOLF_COURSE_ID`: default `--course` value.

Resolution order for ids:

1. explicit flag (`--club`, `--course`)
2. env var (`MINGOLF_CLUB_ID`, `MINGOLF_COURSE_ID`)
3. usage error

## Secure password storage by platform

Use this when CLI workflows need a password without hardcoding secrets in
scripts.

### macOS (Keychain via osascript)

Create a keychain item once:

```bash
security add-generic-password \
  -a "$USER" \
  -s "mingolf-cli-password" \
  -w "<your-password>" \
  -U
```

Read the password at runtime:

```bash
MINGOLF_PASSWORD="$(
  osascript \
    -e 'tell application "System Events"' \
    -e 'get password of generic keychain item "mingolf-cli-password"' \
    -e 'end tell'
)"
```

### Windows (Credential Manager)

Store credentials once in PowerShell:

```powershell
cmdkey /generic:mingolf-cli `
  /user:your-username `
  /pass:your-password
```

Read credentials at runtime (CredentialManager module):

```powershell
$cred = Get-StoredCredential -Target "mingolf-cli"
$env:MINGOLF_USERNAME = $cred.UserName
$env:MINGOLF_PASSWORD = $cred.GetNetworkCredential().Password
```

### Linux (libsecret via secret-tool)

Store password once:

```bash
printf '%s' "<your-password>" | \
  secret-tool store --label="mingolf-cli password" \
  service mingolf-cli account "$USER"
```

Read password at runtime:

```bash
MINGOLF_PASSWORD="$(
  secret-tool lookup service mingolf-cli account "$USER"
)"
```

Recommended automation pattern:

```bash
# Use interactive login if no password flag is available in your version.
mingolf auth login
unset MINGOLF_PASSWORD
```

Notes:

- macOS may prompt for Keychain access on first use.
- Windows example requires the CredentialManager PowerShell module.
- Linux example requires `libsecret` tools (`secret-tool`).
- Prefer `"$()"` command substitution to preserve special characters.
- Avoid echoing passwords or storing them in shell history.

## Commands reference

### Auth

```bash
mingolf auth login
mingolf auth status
mingolf auth logout
mingolf auth logout --forget-creds
```

### Profile

```bash
mingolf profile
```

### Discovery

```bash
mingolf clubs
mingolf clubs --search "chalmers"
mingolf courses --club <clubId>
mingolf tee-times --club <clubId> --course <courseId> --date 2026-05-08
```

### Bookings

```bash
mingolf bookings list
mingolf bookings create --slot <slotId>
mingolf bookings create --slot <slotId> --tee <teeId-or-teeName>
mingolf bookings cancel --booking <bookingId>
```

## Common workflows

### Workflow: first-time setup and check

1. Run `mingolf auth login`.
2. Run `mingolf auth status`.
3. Confirm JSON shows `authenticated: true`.

### Workflow: discover and book a slot

1. Run `mingolf clubs --search "<name>"` and pick `clubId`.
2. Run `mingolf courses --club <clubId>` and pick `courseId`.
3. Run `mingolf tee-times --club <clubId> --course <courseId> --date <date>`.
4. Pick `slotId` from `slots[].slotId`.
5. Run `mingolf bookings create --slot <slotId>`.
6. Save returned `bookings[0].bookingId`.

### Workflow: list and cancel

1. Run `mingolf bookings list`.
2. Find `bookingId` in future rounds.
3. Run `mingolf bookings cancel --booking <bookingId>`.

## Error reference

| Error code | Typical cause | Recovery |
|---|---|---|
| `missing_club_id` | no `--club` and no env default | set `--club` |
|  |  | or `MINGOLF_CLUB_ID` |
| `missing_course_id` | no `--course` and no env default | set `--course` |
|  |  | or `MINGOLF_COURSE_ID` |
| `auth_required` | expired or missing session | run `mingolf auth login` |
| `booking_validation_failed` | API validation errors | inspect |
|  |  | `details.errors`, choose new slot |
| `missing_tee_options` | upstream tee lookup failed | retry or |
|  |  | try another slot |
| `network_timeout` | upstream timeout | retry command |
| `upstream_error` | API returned error status | inspect `details.response` |

## What NOT to do

- Do not call `bookings create` without `slotId` from `tee-times`.
- Do not assume a club name can be used where `clubId` is required.
- Do not assume a course name can be used where `courseId` is required.
- Do not parse human text when JSON fields are available.
- Do not skip `auth status` checks when running headless workflows.

## Additional references

- Basic examples: `examples/basic.md`
- Advanced examples: `examples/advanced.md`

## Changelog

- `1.0.0`: Initial Mingolf skill release.
