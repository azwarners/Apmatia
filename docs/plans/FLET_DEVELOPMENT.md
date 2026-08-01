# Flet Development Guide

## Development Command

To run the Flet client during development:

```bash
cd /home/nick/ServerData/repos/apmatia
./run-flet.sh
```

Start Core separately first with `./start.sh core`. The launcher script uses
the project-local environment and starts the native Apmatia Linux Client.

The current project-local environment reports Flet `0.86.4`. Verify the
installed version before relying on Flet APIs because the migration plan treats
the installed version as authoritative.

The Core API is mounted under `/api`. The current startup connectivity probe is
`GET http://localhost:8000/api/version`; authentication endpoints are under the
same prefix.

## Testing Phase 1

1. Start Apmatia Core:
```bash
./start.sh core
```

2. In another terminal, run Flet:
```bash
./run-flet.sh
```

3. Verify:
- Flet window opens
- Diagnostic screen displays
- Application title shows "Apmatia"
- No errors in terminal or flet_debug.log

## Logging

Connection and error logs are written to the console and `flet_debug.log`.
Routine Flet framework INFO messages are suppressed. The first launch may
still show Flet's one-time desktop-runtime download and installation output.

## Next Steps

After Phase 1 is approved by Nick, proceed to Phase 2: Login Journey. Existing
exploratory login code is retained, but it is not considered Phase 2 complete
until it is reconciled with the real cookie-based API contract and the Phase 2
acceptance tests.

## Phase 2: Login Journey

The Linux client now renders the Core-provided `auth.login.view`, submits the
existing `auth.login` contract, retains the server-owned cookie in its HTTP
session, protects the authenticated placeholder route, and logs out through
the existing `/api/auth/logout` endpoint.

Play-test with Core running:

```bash
./run-flet.sh
```

Verify anonymous startup shows the portable Sign In form, valid credentials
reach the protected Linux placeholder, invalid credentials remain on the login
screen with a visible error, and Log out returns to login. Automated coverage
for the journey is in `tests/unit/test_flet_phase2.py`; the full suite passed
598 tests after the Phase 2 implementation.

The Linux placeholder is intentionally diagnostic. The desktop shell and real
module navigation remain Phase 3 work.
