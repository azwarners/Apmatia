# Migrating Apmatia to Flet

## Linux-First Execution Plan

## Purpose

This document is the execution plan for building the **Apmatia Linux Client** with Flet and replacing the existing Streamlit GUI after behavioral parity is proven.

The first concrete product is not a generic "Flet adapter." It is:

> **Apmatia Linux Client** — a native desktop client that connects to the headless Apmatia Core over Apmatia's existing API and portable view-contract boundary.

A later **Apmatia Android Client** may reuse compatible rendering, state, API, and effect infrastructure. Android is not part of the initial Linux migration and must not weaken or constrain the Linux desktop experience prematurely.

The migration will proceed through small, working vertical slices. The first complete user journey is login, protected navigation, and logout—not the entire component catalog.

The first milestone is:

> Launch the Apmatia Linux Client as a native Flet desktop window, connect it to Apmatia Core, render the existing portable login view, authenticate through Core, navigate to a protected placeholder screen, and log out successfully.

The migration is complete only when supported Linux workflows have behavioral parity, the Linux client can be packaged and released, and Streamlit can be removed without moving module-specific behavior into the client shell.

---

# 1. Product and Platform Boundary

## 1.1 Apmatia Core

Apmatia Core remains a headless Python service. It may run locally, in a container, on a home server, or on another reachable host.

Apmatia Core owns:

- authentication and authorization
- user and session validation
- module discovery
- normalized portable view documents
- view-model data
- intent handling
- server-scoped state
- domain validation
- persistence
- background work
- agent execution
- polling or streaming sources exposed through the API

The Flet migration must not quietly move these responsibilities into the GUI process.

## 1.2 Apmatia Linux Client

The Apmatia Linux Client is the first Flet application and the primary desktop experience.

It owns:

- launching as a native Linux desktop application
- connecting to Apmatia Core
- rendering portable view documents as Flet controls
- collecting keyboard and pointer input
- emitting portable intents to Core
- applying client-side effects
- desktop routing and navigation presentation
- view-scoped and client-session-scoped state
- dialogs, notifications, clipboard integration, file dialogs, and other desktop presentation behavior
- Linux-specific shell layout and interaction patterns

The Linux client may use desktop-oriented layouts such as sidebars, navigation rails, split panes, dense tables, terminal-style output, and keyboard shortcuts.

## 1.3 Apmatia Android Client

The Android client is a later, separate client application.

It may reuse:

- the portable view contract
- API client abstractions
- generic renderer dispatch
- common effect semantics
- selected component renderers
- shared tests where behavior is truly platform-neutral

It will likely require its own:

- application entry point
- navigation shell
- responsive layout decisions
- system-back handling
- lifecycle handling
- mobile file and image pickers
- keyboard behavior
- touch interaction rules
- reduced or adapted presentation for desktop-heavy views

The Android client must be designed after the Linux client proves the architecture. Shared code should be extracted from demonstrated commonality, not speculative symmetry.

---

# 2. Existing Architectural Boundary

Apmatia already has the boundary required for this migration:

- `core/view_contract/` defines framework-neutral view documents, components, data sources, state declarations, intents, effects, and refresh policies.
- Production modules contribute views through their own `views.py` files.
- Apmatia Core exposes normalized view documents and view models through its internal HTTP API.
- The existing text adapter demonstrates that view documents are not inherently tied to Streamlit.
- The GUI shell is expected to remain generic and must not contain module-specific rendering branches.

Flet is therefore a **client implementation of the portable view contract**, not a replacement for module behavior.

## Architectural rule

> Modules describe views and behavior through portable contracts. Apmatia Core remains authoritative. The Linux client renders, collects input, emits intents, and presents results.

The Linux client must not import module internals merely to make a screen work.

---

# 3. Development Workflow

## 3.1 Project-local dependency management

Flet must be installed as a declared dependency in Apmatia's project-local environment.

Do not:

- install Flet into the system Python environment
- use `sudo pip`
- use `pip install --user` as a substitute for project dependency management
- create a second dependency-management convention without inspecting the repository

Before changing dependencies, inspect:

- `pyproject.toml`
- existing lockfiles
- current virtual-environment conventions
- supported Python versions
- development documentation
- existing application entry points

If Apmatia uses `uv`, the expected workflow is conceptually:

```bash
uv add flet
uv run flet run -m <linux-client-entry-module>
```

The exact command must follow the installed Flet version and Apmatia's package layout.

## 3.2 Development target

All migration development through the Linux release phase targets:

- Linux desktop
- a native Flet application window
- keyboard and pointer interaction
- connection to a running Apmatia Core instance

Development should run from Python source with Flet's supported reload workflow. Do not rebuild a release artifact after every source change.

## 3.3 Release target

Release packaging occurs only after the Linux client works from source and passes its tests.

The expected packaging step is conceptually:

```bash
uv run flet build linux
```

The exact command, output structure, and required toolchain must be verified against the installed Flet version.

## 3.4 Repository safety

Do not run a Flet project-generation command inside the Apmatia repository unless its overwrite behavior has been reviewed.

Apmatia already has project metadata and an established source tree. The migration should add a Linux client, not replace repository files with a generated template.

---

# 4. Migration Principles

## 4.1 Build vertical slices

Each phase must produce a working end-to-end capability. Avoid building dozens of disconnected controls before any real workflow works.

## 4.2 Name the product being built

Every phase before Android work begins is part of the **Apmatia Linux Client**. Generic shared infrastructure may emerge, but the runnable product and acceptance criteria must remain explicit.

## 4.3 Keep portable contracts platform-neutral

The view contract should not contain Flet-specific controls or Linux-only implementation details.

Platform-specific presentation belongs in the Linux client.

## 4.4 Keep renderer dispatch generic

The initial renderer may support only a few component types, but dispatch must be based on portable component types rather than hard-coded knowledge of login, users, discussions, or another module.

## 4.5 Fail visibly on unsupported features

Unsupported component types, effects, field variants, and refresh modes must produce useful development errors. They must not disappear silently.

## 4.6 Verify Flet APIs against the installed version

This document defines required behavior, not unquestionable method names.

Before implementation, verify the installed Flet version's current APIs for:

- application startup
- desktop window configuration
- routing and route changes
- view stacks and back navigation
- client/session storage
- secure token storage
- async work
- polling and cancellation
- dialogs and notifications
- file dialogs
- clipboard support
- testing
- Linux packaging
- Android packaging when that phase begins

Do not introduce deprecated methods merely because they appear in old examples.

## 4.7 Prefer behavioral parity over visual imitation

The goal is to preserve workflows and semantics, not reproduce Streamlit's appearance.

The Linux client should feel like a deliberate desktop application.

---

# 5. Proposed Client Structure

The exact paths may be adjusted to fit the repository. The important requirement is to separate the concrete Linux application from infrastructure that may later become shareable.

In Apmatia's current package layout, the concrete Linux client lives under
`src/apmatia/interfaces/flet/linux/`. Platform-neutral Flet infrastructure
remains alongside that package until a later client proves that it should be
shared.

```text
clients/
├── common/
│   ├── __init__.py
│   ├── api_client.py          # Framework-neutral client for Apmatia Core
│   ├── contracts.py           # Client-side protocol helpers, if needed
│   └── errors.py
├── flet_common/
│   ├── __init__.py
│   ├── renderer.py            # Generic ViewComponent dispatcher
│   ├── state.py               # Client view/session-state abstraction
│   ├── effects.py             # Portable effect execution
│   ├── bindings.py            # Field and intent bindings
│   └── components/
│       ├── __init__.py
│       ├── page.py
│       ├── panel.py
│       ├── text.py
│       ├── field.py
│       ├── actions.py
│       └── notice.py
└── linux/
    ├── __init__.py
    ├── main.py                # Linux Flet entry point
    ├── app.py                 # Dependency wiring and startup
    ├── shell.py               # Linux desktop shell
    ├── router.py              # Linux route handling
    ├── platform.py            # Linux-specific integrations
    ├── configuration.py       # Core endpoint and client settings
    └── tests/
        ├── test_startup.py
        ├── test_login_journey.py
        ├── test_routes.py
        └── test_shell.py
```

This structure is illustrative, not mandatory.

Do not create one source file for every possible future component before that component is needed.

## 5.1 Phase Approval Gates

Each phase is a review boundary. Work discovered or implemented ahead of its
phase may be retained as exploratory work, but it does not count as phase
completion until its own acceptance criteria have been demonstrated.

At the end of each phase:

1. Record the deliverables and verification evidence.
2. Review deviations, unfinished work, and exploratory implementation.
3. Obtain explicit Nick approval before treating the next phase as authorized.

Early implementation must not be discarded solely because it arrived before
the phase gate. It should be reviewed against the relevant phase contract and
kept, revised, or deferred as appropriate.

## 5.2 Pre-Phase 1 Baseline

The repository baseline for the next phase is:

- The project uses `pyproject.toml` for dependencies and has a project-local
  `.venv`; Flet is currently declared without a version pin.
- The installed development environment currently reports Flet `0.86.4`.
- The FastAPI application mounts its HTTP router at `/api`.
- The existing Core startup probe is `GET /api/version`; no `/health` route is
  currently defined.
- Public authentication documents are available at `GET /api/auth/views`.
- Authentication uses `POST /api/auth/login`, `GET /api/auth/session`, and
  `POST /api/auth/logout`.
- Authentication is cookie-based using the `apmatia_session` HTTP-only cookie;
  the client must preserve and clear that cookie according to the existing API
  behavior.
- Streamlit remains the existing interface and must continue using its current
  startup path while the Flet client is developed separately.

The existing exploratory Flet implementation does not yet establish this
baseline: its API client currently defaults to a base URL without the `/api`
prefix, and its launcher is not yet wired to Core. These are Phase 1 review
items, not reasons to discard the exploratory work.

---

# Phase 0: Confirm the Linux-First Product Boundary

## Goal

Record the product decision before implementation begins.

If exploratory implementation has already begun, Phase 0 remains a valid
architecture and scope decision; the existing implementation is treated as
unapproved work-in-progress until reviewed at the appropriate later phase.

## Required decisions

Document that:

- the first Flet product is the Apmatia Linux Client
- Linux desktop is the development and testing target
- the Linux client connects to headless Apmatia Core
- Streamlit remains available during migration
- Android is deferred until after the Linux client proves the architecture
- Android reuse is desirable but not guaranteed for every shell, layout, or component
- Linux-specific desktop behavior is allowed and expected

## Deliverable

A short architecture note, ADR, or approved section of project documentation describing the boundary.

## Acceptance criteria

- The repository and implementation plan clearly name the Apmatia Linux Client.
- No phase treats the first seven steps as an unspecified generic client.
- Android work is explicitly out of scope until the later Android phase.

---

# Phase 1: Bootstrap the Apmatia Linux Client

## Goal

Launch a native Apmatia Flet desktop window on Linux from the project-local environment.

## Scope

Implement:

- project-local Flet dependency
- Linux client entry module
- application title
- initial window sizing and minimum size where supported
- icon placeholder or existing Apmatia icon wiring
- Linux client configuration
- Apmatia Core endpoint configuration
- Core health check
- visible startup, connection, and configuration errors
- startup logging
- documented development command

Do not yet replace Streamlit or remove any existing GUI entry point.

## Initial flow

```text
Run Linux client from project environment
    ↓
Open native Flet desktop window
    ↓
Load client configuration
    ↓
Check Apmatia Core health
    ↓
Success: show temporary connected screen
Failure: show actionable connection error
```

## Acceptance criteria

- A native desktop window opens on Linux.
- The window is identified as Apmatia.
- No system-wide Flet installation is required.
- The client can connect to the configured Apmatia Core endpoint.
- An unavailable Core produces a useful visible error rather than a blank or crashed window.
- Source changes can be exercised through the supported Flet development command.
- Existing Streamlit behavior and existing tests still work.

## Phase 1 approval boundary

Phase 1 is complete only after the launcher has been tested against the actual
Core surface documented in the pre-Phase 1 baseline. The connected state must
show the Core version from `/api/version`; the disconnected state must show an
actionable error when that endpoint is unavailable. Login, portable view
rendering, session-state architecture, protected navigation, and logout remain
later work even if exploratory code for them is already present.

---

# Phase 2: Linux Login Journey — First Vertical Slice

## Goal

Complete login, protected navigation, and logout in the Apmatia Linux Client using the existing portable authentication contract.

## Required discovery

Before coding the screen, locate and document:

- the current portable login view document
- login field identifiers
- login intent name and payload
- the API path or client method used to submit the intent
- authentication success and failure response shapes
- token, cookie, or session behavior
- logout behavior
- protected-route behavior
- any existing authentication tests

Do not invent a second authentication API when one already exists.

## End-to-end flow

```text
Start Apmatia Linux Client
    ↓
Resolve initial route
    ↓
Unauthenticated client requests portable login view
    ↓
Generic Flet renderer builds controls
    ↓
User enters credentials and activates Login
    ↓
Client emits existing login intent to Core
    ↓
Core authenticates user
    ↓
Failure: show visible error
Success: establish authenticated client state
    ↓
Navigate to protected Linux placeholder screen
    ↓
Logout clears authentication and returns to login
```

## Minimum component support

Implement only the components required by the real login document, likely including some subset of:

- `page`
- `panel` or `card`
- `text`
- `field:text`
- `field:password`
- `actions`
- `notice`

Inspect the actual contract rather than assuming this list is exact.

## Minimum effect support

Implement only effects required by the real journey, likely including some subset of:

- `set_state`
- `clear_state`
- `navigate`
- `show_notification`
- `refresh_view`

## Authentication-state requirements

Define client state by behavior before selecting a Flet storage API.

Distinguish:

- transient event and form state
- view-scoped state
- state retained across navigation during the client session
- sensitive authentication material
- server-owned session state

Do not store passwords.

Do not place long-lived authentication secrets in ordinary preference storage. Follow Apmatia's existing session model and use appropriate storage for the Linux platform.

## Protected placeholder

After successful login, show a minimal protected Linux screen containing:

- authenticated identity summary
- Core connection state
- confirmation that the Linux authentication slice succeeded
- Logout action

This is a diagnostic destination, not the final dashboard.

## Acceptance criteria

### Successful login

- The real portable login view is rendered.
- Valid credentials are accepted by Apmatia Core.
- Authentication state survives navigation to the protected placeholder.
- The protected route identifies the authenticated user.

### Failed login

- Invalid credentials produce a visible error.
- No authenticated state is created.
- Password handling follows existing security behavior.
- Username retention follows the existing UX or an explicitly approved replacement.

### Route protection

- Opening a protected route while unauthenticated leads to login.
- Logging out makes protected routes inaccessible.
- Back navigation does not reveal a usable authenticated screen after logout.

### Architecture

- Login behavior is not hard-coded into generic renderer dispatch.
- Core remains authoritative for authentication.
- Unsupported contract features fail clearly.

### Tests

Add automated coverage for:

- login document rendering
- field-state updates
- login intent payload
- successful login
- failed login
- protected-route redirection
- session state across route changes
- logout

---

# Phase 3: Linux Desktop Shell and Module Navigation

## Goal

Replace the protected placeholder with the first real Linux desktop shell.

## Scope

Implement:

- authenticated application shell
- Linux desktop sidebar, navigation rail, or equivalent
- generic module catalog
- route-to-view resolution
- window resizing behavior
- loading, empty, unauthorized, disconnected, and error states
- user/session menu
- logout
- theme preference wiring where supported
- predictable keyboard and pointer navigation

## Linux-specific expectations

The shell may use:

- persistent left navigation
- desktop-width content areas
- split panes
- keyboard shortcuts
- hover states
- context menus where appropriate

These behaviors belong to the Linux presentation layer and do not need to be encoded into portable module logic.

## Routing requirements

Use the current supported Flet routing model for the installed version.

The router must:

- distinguish public and protected routes
- rebuild route-level views consistently
- handle desktop back behavior
- restore a sensible route after reconnect or restart where appropriate
- avoid deprecated navigation helpers
- contain no module-specific route branches beyond generic identifiers and metadata

## Acceptance criteria

- An authenticated Linux user can see the module catalog.
- Selecting a module resolves a portable view through Core.
- Revisiting a route produces a consistent result.
- Unauthorized and disconnected states are deliberate and visible.
- Back navigation behaves predictably.
- The shell contains no module-specific rendering branches.

---

# Phase 4: First Simple Production Module on Linux

## Goal

Prove the Linux client works beyond authentication by porting one stable, ordinary production workflow.

## Module selection criteria

Choose a stable module that exercises several common controls without requiring streaming.

Prefer a module with:

- a collection or table
- selection
- a detail area
- a small form
- one or more actions
- straightforward refresh behavior

Do not begin with Discussions or Agent Loops.

## Likely component expansion

Implement only what the chosen module requires, such as:

- `columns`
- `collection`
- `table`
- `form`
- additional field variants
- `detail`
- `status`
- secondary actions
- destructive actions
- confirmation dialogs

## Linux UX expectations

Use desktop-appropriate presentation, including:

- master/detail layout where useful
- dense tables where appropriate
- keyboard focus order
- resizable content
- clear pointer selection states

## Acceptance criteria

- One real production workflow works end to end in the Linux client.
- Selection and form state behave correctly.
- Intents use the shared adapter path.
- Data refreshes without restarting the client.
- Component additions have renderer tests.
- No module-specific logic is added to the shell.

---

# Phase 5: Discussions on Linux

## Goal

Port Discussions and establish the Linux desktop pattern for conversational views.

## Scope

Implement the actual contract features required for:

- discussion navigation
- message timeline
- message cards
- composer
- send action
- loading and failure states
- automatic scrolling behavior
- polling or streaming according to the existing contract
- desktop keyboard submission

## Linux presentation expectations

The Linux client may provide:

- discussion list and active timeline in a split view
- wider message layout
- keyboard shortcuts
- multiline composer behavior suited to desktop use
- clipboard and attachment integration where supported

## Research questions

Verify with the installed Flet version:

- efficient incremental list updates
- auto-scroll behavior
- behavior when the user reads older messages
- desktop keyboard submission
- multiline text entry
- attachment selection and upload if currently supported
- lifecycle-safe polling or stream cancellation

## Acceptance criteria

- Existing discussions can be opened.
- Messages render in correct order.
- Sending uses the existing intent/API path.
- Duplicate and stale updates are rejected according to the contract.
- The client does not force-scroll a user reading older messages.
- Polling or streaming stops when leaving the view.
- Re-entering reconstructs current server-authoritative state.

---

# Phase 6: Agent Loops on Linux

## Goal

Port Agent Loops and establish safe, efficient handling of terminal-style live output on Linux.

## Scope

Implement the contract features required for:

- terminal-style output
- progress state
- checklist state
- start and stop actions
- append-oriented updates
- reconnect or refresh behavior
- stale-event rejection
- lifecycle cleanup

## Linux presentation expectations

The Linux client may provide:

- dense monospaced output
- wide terminal panes
- split views
- keyboard text selection and copy
- explicit follow-tail behavior
- desktop task controls

## Research questions

Verify:

- efficient large-list rendering
- whether virtualization is needed
- batching updates to avoid excessive redraws
- text selection and copy behavior
- monospaced typography
- retained-line or log-window limits
- cancellation when navigating away
- reconstruction after reconnect

## Acceptance criteria

- Live output updates without freezing the Linux client.
- Output ordering remains correct.
- UI updates are batched where necessary.
- Start, stop, progress, and checklist state remain synchronized with Core.
- Leaving the view cleans up subscriptions or polling.
- Re-entering reconstructs current server-authoritative state.

---

# Phase 7: Expand Linux Contract Coverage

## Goal

Support the remaining production Linux views based on actual need rather than implementing every theoretical component in advance.

## Possible additions

Depending on production demand:

- `stack`
- `tabs`
- `card`
- `navigation`
- `markdown`
- remaining field variants
- `timeline`
- `message`
- `composer`
- `terminal`
- `progress`
- `checklist`
- `tree`
- `expander`

## Support matrix

Maintain an authoritative support matrix:

| Contract feature | Linux supported | Tested | Used by | Known limitations |
|---|---:|---:|---|---|
| page | yes/no | yes/no | views | notes |
| field:text | yes/no | yes/no | views | notes |
| navigate effect | yes/no | yes/no | views | notes |

The matrix should measure migration status, not the number of renderer files created.

## Acceptance criteria

- Every supported production Linux view renders correctly.
- Unsupported views are deliberately marked unsupported.
- Missing features identify the exact unsupported contract capability.
- No production view silently drops controls or actions.
- Renderer behavior remains module-neutral.

---

# Phase 8: Linux Parity, Hardening, Packaging, and Release

## Goal

Finish and release the Apmatia Linux Client.

## 8.1 Behavioral parity

Test representative Linux journeys, including:

- startup and Core connection
- login
- failed login
- logout
- protected navigation
- module discovery
- ordinary CRUD workflows
- Discussions
- Agent Loops
- reconnect after Core restart
- client restart
- theme and preference behavior
- errors and unauthorized states

Document intentional differences from Streamlit.

## 8.2 Linux integration

Verify:

- application name and icon
- desktop entry behavior
- Wayland behavior
- X11 behavior where relevant
- window sizing and persistence
- clipboard
- file dialogs
- external URL opening
- notifications where appropriate
- keyboard navigation
- high-DPI behavior
- Linux distribution compatibility targets

## 8.3 Packaging

Use the installed Flet version's supported Linux build workflow.

Possible release outputs may include:

- Flet Linux application bundle
- compressed release archive
- `.deb`
- AppImage
- Flatpak later, if desired

Do not promise a single statically linked executable unless the actual build output provides one.

## 8.4 Release criteria

The Linux client is ready for release when:

- it can be built from a clean checkout using documented commands
- the packaged application launches without the development virtual environment
- Core endpoint configuration is documented
- supported workflows pass automated and manual tests
- known limitations are documented
- release artifacts contain required resources
- license and third-party notices are included where required

## 8.5 Streamlit cutover

Remove or archive Streamlit only after:

- Linux parity is accepted
- the packaged Linux client is usable
- rollback is understood
- remaining unsupported workflows are explicitly approved

Do not remove Streamlit merely because the Flet shell launches.

---

# Phase 9: Design and Build the Apmatia Android Client

## Goal

Create a separate Android client after the Linux client and shared Flet infrastructure have been proven.

## Discovery

Before implementation:

- identify which Linux code is genuinely portable
- identify desktop-only shell behavior
- identify views requiring mobile adaptation
- determine Android lifecycle and storage requirements
- define the supported Android module subset
- decide how the Android client discovers or configures Apmatia Core

## Proposed structure

```text
clients/
├── flet_common/
│   └── ...proven shared infrastructure...
└── android/
    ├── __init__.py
    ├── main.py
    ├── app.py
    ├── shell.py
    ├── router.py
    ├── platform.py
    └── tests/
```

## Android-specific concerns

- touch target size
- narrow and responsive layouts
- system-back behavior
- software keyboard behavior
- pause and resume lifecycle
- network changes
- secure storage
- file and image selection
- permissions
- notification behavior
- app backgrounding
- APK build and installation

## Reuse rule

> Reuse portable behavior and proven common Flet infrastructure. Do not force Linux shell code or desktop layouts into Android merely to maximize shared lines of code.

## Acceptance criteria

- Android has its own explicit application entry point.
- Login works against Apmatia Core.
- Mobile navigation is intentional.
- Supported modules are documented.
- Unsupported desktop-heavy views fail deliberately or provide approved mobile presentations.
- APK packaging and installation are documented and tested.

---

# 6. State Model

The portable contract defines four conceptual scopes:

- `event`
- `view`
- `session`
- `server`

The Linux implementation must preserve these semantics without assuming that one Flet storage mechanism maps perfectly to every scope.

## Event scope

- transient input or event data
- cleared after intent processing
- not persisted across routes

## View scope

- retained while a view is active
- selection, local form drafts, scroll-related state where appropriate
- disposed or archived when the view lifecycle ends

## Session scope

- retained across navigation during the Linux client session
- authenticated identity summary
- shell preferences
- current user context

## Server scope

- owned by Apmatia Core
- read and changed through API calls and intents
- never treated as authoritative merely because a client copy exists

## Sensitive authentication material

Handle separately from ordinary UI state.

The implementation must follow Apmatia's actual authentication model and the secure storage capabilities available on Linux.

---

# 7. Effects

Implement effects incrementally, driven by real production journeys.

Likely effects include:

- `set_state`
- `clear_state`
- `select_item`
- `navigate`
- `open_panel`
- `close_panel`
- `show_notification`
- `refresh_source`
- `refresh_view`
- `start_polling`
- `stop_polling`
- `download`

## Rules

- Core remains authoritative for domain changes.
- Client effects must be testable.
- Unsupported effects must fail clearly.
- Polling and streams must be cancelled when their view is disposed.
- Stale responses must not overwrite newer state.
- UI refresh behavior must follow the current Flet version rather than old Streamlit assumptions.

---

# 8. Error Handling

The Linux client must provide explicit states for:

- Core unavailable
- request timeout
- authentication failure
- authorization failure
- malformed view document
- unsupported component
- unsupported effect
- stale response
- disconnected live stream
- unexpected client error

Development errors should contain useful contract identifiers and routes.

User-facing errors should explain what happened and what action is possible without exposing secrets.

---

# 9. Testing Strategy

## 9.1 Unit tests

Test:

- component dispatch
- field bindings
- intent payload generation
- state-scope behavior
- effect execution
- unsupported-feature errors
- route guards

## 9.2 Contract tests

Feed representative portable view documents into the renderer and verify:

- correct control tree
- stable component identifiers
- input binding
- intent emission
- error behavior

## 9.3 Integration tests

Test the Linux client against Apmatia Core for:

- health check
- login
- failed login
- logout
- module catalog
- view loading
- intent submission
- refresh
- reconnect

## 9.4 Journey tests

Cover representative end-to-end Linux journeys:

- launch and connect
- authenticate
- navigate to module
- select an item
- edit or create data
- send a discussion message
- start and observe an agent loop
- logout

## 9.5 Manual Linux testing

Test on the Linux distributions and display stacks Apmatia intends to support.

Record:

- distribution
- desktop environment
- Wayland or X11
- Python/build environment
- packaged artifact tested
- known issues

---

# 10. Definition of Done

## Linux migration complete

The Flet migration is complete when:

- the Apmatia Linux Client is an explicit, documented product
- it launches as a native Linux desktop application
- it connects to headless Apmatia Core
- supported production workflows have accepted behavioral parity
- module-specific logic remains outside the generic shell and renderer
- the portable view contract remains framework-neutral
- unsupported features fail clearly
- automated and manual Linux tests pass
- a clean, documented Linux build produces releasable artifacts
- Streamlit can be removed or archived without losing approved workflows

## Android not implied

Completion of the Linux migration does not imply Android parity.

The Android client is a separate later product phase with its own scope, acceptance criteria, packaging, and release process.

---

# 11. Immediate Implementation Assignment

The next implementation task should be narrowly scoped:

> Bootstrap the Apmatia Linux Client in Flet using the repository's project-local dependency workflow. Launch a native Linux desktop window, load configuration, connect to Apmatia Core, and display a useful connected or disconnected startup screen. Do not install Flet system-wide, replace Streamlit, implement the complete renderer, or begin Android work.

After that succeeds, proceed to the portable login journey in Phase 2.
