# Basic Mingolf examples

## Login and status

```bash
mingolf auth login
mingolf auth status
```

Expected pattern:

- `auth login` returns `ok: true`.
- `auth status` returns `authenticated: true`.

## Club and course lookup

```bash
mingolf clubs --search "chalmers"
mingolf courses --club 9c0e75f1-0f2e-4b75-961d-608841060bdf
```

Expected pattern:

- first command returns `clubs` array.
- second command returns `courses` array for given `clubId`.

## Tee times with explicit ids

```bash
mingolf tee-times \
  --club 9c0e75f1-0f2e-4b75-961d-608841060bdf \
  --course 8d508bb7-3229-41f2-914a-8ab20453dd61 \
  --date 2026-05-08
```

Expected pattern:

- output has `slots` array.
- each slot includes `slotId`, `timeUtc`, and `bookable`.

## Book and cancel

```bash
mingolf bookings create --slot 724854b6-b739-4886-b9e1-a545103763a1
mingolf bookings list
mingolf bookings cancel --booking dbd9f886-0ec9-4434-bc3f-3968bd371970
```
