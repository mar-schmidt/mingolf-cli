# Mingolf API notes for CLI usage

This document summarizes the Mingolf API used by mingolf.golf.se.
It is also used by `mingolf-cli` which focuses on practical flows and minimum fields needed for
automation.

Base URL:

- `https://mingolf.golf.se`

Auth model:

- cookie-based session, no bearer token

## 1) Authentication

### Login

- `POST /login/api/Users/Login`
- body:
  - `golfId`
  - `password`
- success:
  - sets session cookie
  - may return sparse profile fields in some cases

### Profile check

- `GET /login/api/profile`
- use this to verify active session
- returns canonical profile data

### Logout

- `POST /login/api/logout`

## 2) Core entities

- `clubId`: golf club UUID
- `courseId`: course UUID inside club
- `slotId`: tee-time UUID
- `bookingId`: booking UUID for cancellation

## 3) Discovery flow

### List clubs

- `GET /bokning/api/Clubs`
- fields used:
  - `id`
  - `name`

### List courses for a club

- source endpoint:
  - `GET /hcp/api/Clubs/Courses`
- select one club by `id`
- fields used:
  - `courses[].id`
  - `courses[].name`

### List tee times

- `GET /bokning/api/Clubs/{clubId}/CourseSchedule`
- query:
  - `courseId`
  - `date` (`YYYY-MM-DD`)
- fields used:
  - `slots[].id`
  - `slots[].time`
  - `slots[].isLocked`
  - `slots[].availablity.bookable`
  - `slots[].availablity.availableSlots`

## 4) Booking flow

Required sequence:

1. lock slot
2. validate payload
3. fetch tee options
4. create booking

### Lock

- `POST /bokning/api/Slot/{slotId}/Lock`

### Validate

- `POST /bokning/api/Slot/{slotId}/Bookings/Validate`
- payload includes:
  - `slotBookingId` (generated, temporary)
  - `player` profile fields
- stop if `errors` is non-empty

### Tee options

- `POST /bokning/api/Slot/{slotId}/Players/PlayingHandicaps`
- used to pick default or requested tee

### Create

- `POST /bokning/api/Slot/{slotId}/Bookings`
- returns booking data including `bookingId`

### Cleanup on failure

- if lock succeeded but later step fails:
  - `DELETE /bokning/api/Slot/{slotId}/Lock`

## 5) Booking management

### List current/future bookings

- `GET /start/api/Persons/HomeOverview`
- read:
  - `golfCalender.futureRounds`
  - `futureRounds[].bookingInfo.bookingId`

### Cancel booking

- `DELETE /bokning/api/Slot/Bookings/{bookingId}`

## 6) Error patterns

Common statuses:

- `200` success
- `204` success, no content
- `400` validation or bad request
- `401` or `403` missing/expired session
- `404` unavailable endpoint/feature
- `503` temporary backend issues

Notable auth behavior:

- login failures can return Swedish string messages, not structured objects

## 7) CLI mapping

- `mingolf auth login` -> login endpoint + profile check
- `mingolf auth status` -> profile endpoint
- `mingolf clubs` -> clubs endpoint
- `mingolf courses --club` -> clubs/courses endpoint
- `mingolf tee-times` -> course schedule endpoint
- `mingolf bookings create` -> lock/validate/tees/create sequence
- `mingolf bookings list` -> home overview endpoint
- `mingolf bookings cancel` -> cancel endpoint
