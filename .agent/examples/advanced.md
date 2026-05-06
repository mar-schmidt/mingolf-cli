# Advanced Mingolf examples

## Headless defaults with env vars

```bash
export MINGOLF_CLUB_ID="9c0e75f1-0f2e-4b75-961d-608841060bdf"
export MINGOLF_COURSE_ID="8d508bb7-3229-41f2-914a-8ab20453dd61"
mingolf tee-times --date 2026-05-08
```

This uses env defaults when `--club` and `--course` are not passed.

## Custom auth-state path for automation

```bash
export MINGOLF_CLI_AUTH_STATE_PATH="$PWD/.tmp/auth_state.json"
mingolf auth login --golf-id "<golf-id>" --password "<password>"
mingolf auth status
```

Useful for CI, ephemeral shells, and isolated automation contexts.

## JSON chaining pattern

```bash
SLOT_ID="$(mingolf tee-times \
  --club "$MINGOLF_CLUB_ID" \
  --course "$MINGOLF_COURSE_ID" \
  --date 2026-05-08 \
  | jq -r '.slots[] | select(.bookable == true) | .slotId' \
  | head -n 1)"

mingolf bookings create --slot "$SLOT_ID"
```

Use stable JSON keys rather than parsing prose output.

## Tee override when creating booking

```bash
mingolf bookings create \
  --slot 724854b6-b739-4886-b9e1-a545103763a1 \
  --tee 8b1baba1-744b-4a39-ba89-785665216106
```

`--tee` accepts either tee id or tee name.

## Cross-platform secure password retrieval

Use OS credential stores instead of plaintext env vars.

macOS:

```bash
MINGOLF_PASSWORD="$(
  osascript \
    -e 'tell application "System Events"' \
    -e 'get password of generic keychain item "mingolf-cli-password"' \
    -e 'end tell'
)"
mingolf auth login
unset MINGOLF_PASSWORD
```

Windows PowerShell:

```powershell
$cred = Get-StoredCredential -Target "mingolf-cli"
$env:MINGOLF_USERNAME = $cred.UserName
$env:MINGOLF_PASSWORD = $cred.GetNetworkCredential().Password
mingolf auth login
Remove-Item Env:\MINGOLF_PASSWORD
```

Linux:

```bash
MINGOLF_PASSWORD="$(
  secret-tool lookup service mingolf-cli account "$USER"
)"
mingolf auth login
unset MINGOLF_PASSWORD
```
