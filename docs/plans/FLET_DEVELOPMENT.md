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

## Phase 3: Linux Desktop Shell and Module Navigation

The authenticated Linux client now loads the generic module catalog from Core,
renders a persistent desktop navigation rail, and resolves selected views from
the portable `/module-views/{view_id}/document` contract. Unsupported view
components produce an explicit message rather than a blank client; production
workflow controls remain Phase 4 work.

Play-test with Core running:

```bash
./run-flet.sh
```

After signing in, verify that the module catalog appears on the left, Home
returns to the shell landing view, selecting a view changes the route and
loads its portable document, and Log out returns to the login screen.

## Phase 4: Users module workflow

The stable Users module is the first Phase 4 production workflow. The shared
Flet renderer now supports its portable collection/table, create and edit
forms, field variants, delete/disable action, Core-backed data refresh, and
generic module-command execution.

Play-test with Core running:

```bash
./run-flet.sh
```

After signing in, open Users from the navigation rail. Verify that the user
collection loads, Create opens the form, Edit pre-populates the selected row,
Delete / Disable refreshes the collection, and newly created or edited data is
visible without restarting the client.

## Phase 4.5: AI Model Manager

AI Model Manager is the next migration slice because Discussions and Agent
Loops depend on model inventory and endpoint configuration. Its three stable
views use the existing schema-generated collection contract: GGUF Models, LLM
Configs, and Task Preferences.

The shared Flet renderer now merges document-level command metadata into
component action keys, allowing schema-generated forms and tables to execute
their Core commands without module-specific shell code.

Play-test with Core running:

```bash
./run-flet.sh
```

Verify that the three AI Model Manager views appear in the navigation, existing
records load, forms open and submit, model records can be edited, and LLM API
keys remain masked and absent from terminal output.
