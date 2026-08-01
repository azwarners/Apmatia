# Migrating Apmatia to Flet

## Purpose

This document is the execution plan for replacing Apmatia's Streamlit GUI with a Flet-based Linux client while preserving Apmatia's framework-neutral architecture.

The migration will proceed through small, working vertical slices. The first slice is the complete login journey—not the full component catalog.

The immediate goal is:

> Launch the Flet client, render Apmatia's existing portable login view, authenticate against Apmatia Core, establish client authentication state, and navigate to a protected placeholder screen.

The migration is complete only when the Flet client provides behavioral parity for the supported production workflows and Streamlit can be removed without moving module-specific UI logic into the client shell.

---

## Architectural Boundary

Apmatia already has the boundary needed for this migration:

- `core/view_contract/` defines framework-neutral view documents, components, data sources, state declarations, intents, effects, and refresh policies.
- Production modules contribute views through their own `views.py` files.
- Apmatia Core exposes normalized view documents and view models through its internal HTTP API.
- The existing text adapter demonstrates that view documents are not inherently tied to Streamlit.
- The GUI shell is expected to remain generic and must not contain module-specific rendering branches.

Flet is therefore a **client adapter**, not a new source of application behavior.

### Responsibility of Apmatia Core

Apmatia Core owns:

- authentication and authorization
- module discovery
- normalized view documents
- view-model data
- intent handling
- server-scoped state
- domain validation
- persistence
- long-running work and agent execution

### Responsibility of the Flet client

The Flet client owns:

- rendering portable view documents as Flet controls
- collecting user input
- emitting intents to Apmatia Core
- applying client-side effects
- route and navigation presentation
- view-scoped and session-scoped client state
- notifications, dialogs, and other native presentation behavior
- desktop and Android interaction adaptations

The Flet client must not duplicate domain rules that belong in modules or Apmatia Core.

---

## Development Environment

Flet must be installed as a declared dependency in Apmatia's project-local environment.

Do not:

- install Flet into the system Python environment
- use `sudo pip`
- use `pip install --user` as a substitute for project dependency management
- create a second package-management convention without inspecting the repository

Before changing dependencies, inspect:

- `pyproject.toml`
- existing lockfiles
- existing virtual-environment conventions
- development documentation
- current Python version constraints

If Apmatia uses `uv`, the expected workflow is conceptually:

```bash
uv add flet
uv run flet run -m <flet-entry-module>
```

The exact entry module must follow Apmatia's existing package layout.

### Development versus release

During development, run the Python source through the project environment with Flet hot reload. Do not rebuild a Linux release after every code change.

Release packaging is a later phase performed with Flet's platform build command after the client works from source and passes its tests.

### Important repository safety note

Do not run a Flet project-creation command in the Apmatia repository unless its overwrite behavior has been reviewed. Apmatia already has project metadata and an established source tree; the migration should add an adapter, not replace repository files with a generated template.

---

## Migration Principles

### 1. Build vertical slices

Each phase must produce a usable end-to-end journey. Avoid implementing dozens of disconnected controls before any real workflow works.

### 2. Keep the renderer generic

The initial renderer may support only a few component types, but dispatch must be based on the portable component contract rather than hard-coded knowledge of the login module.

### 3. Fail visibly on unsupported contract features

Unsupported component types, effects, field variants, or refresh modes must produce useful development errors. They must not disappear silently.

### 4. Verify Flet APIs against the installed version

This plan defines required behavior, not unquestionable Flet method names. Flet evolves quickly. Before implementation, verify the installed version's current APIs for:

- application startup
- routing and navigation
- view stacks and back navigation
- client/session storage
- secure credential or token storage
- asynchronous work
- polling and cancellation
- dialogs and notifications
- file handling
- testing
- Linux and Android packaging

Deprecated methods must not be introduced merely because they appear in an older example.

### 5. Preserve the client/server boundary

The Linux and Android applications are clients of Apmatia Core. The migration must not quietly collapse Core into the GUI process unless a separately approved deployment mode explicitly calls for it.

### 6. Prefer behavioral parity over visual imitation

The objective is to preserve workflows and semantics. The Flet client may use native layouts and interaction patterns instead of copying Streamlit's appearance.

---

## Proposed Adapter Structure

The exact filenames may be adjusted to fit the repository, but responsibilities should remain separated.

```text
interfaces/flet/
├── __init__.py
├── app.py                 # Flet entry point and dependency wiring
├── shell.py               # Generic application shell
├── router.py              # Route resolution and protected-route handling
├── renderer.py            # Generic ViewComponent dispatcher
├── api_client.py          # HTTP client for Apmatia Core
├── state.py               # Client view/session state abstraction
├── effects.py             # Client-side effect execution
├── errors.py              # Adapter-specific errors
├── components/
│   ├── __init__.py
│   ├── page.py
│   ├── panel.py
│   ├── text.py
│   ├── field.py
│   ├── actions.py
│   └── notice.py
└── tests/
    ├── test_renderer.py
    ├── test_login_journey.py
    ├── test_routes.py
    └── test_effects.py
```

Do not create one file per future component until the component actually needs implementation. The structure should grow with supported behavior.

---

# Phase 0: Repository and Contract Discovery

## Goal

Understand the existing authentication journey and project conventions before writing Flet code.

## Required investigation

Locate and document:

- the current Flet-independent login view document
- the register view document, if relevant to the initial journey
- login field identifiers
- login intent name and payload shape
- the API endpoint or internal client method used to submit that intent
- success and failure response shapes
- authentication token, cookie, or session behavior
- logout intent or endpoint
- protected-route behavior in the current shell
- the normalized view-document API
- the project's dependency-management convention
- existing tests that define authentication behavior

## Deliverable

A short implementation note or code comments identifying the concrete existing contracts that the Flet slice will use.

## Acceptance criteria

- No authentication API is invented when an existing one already exists.
- No module-specific login form is hand-built outside the portable view contract unless a documented contract gap makes that temporarily unavoidable.
- Dependency changes follow the repository's established tooling.

---

# Phase 1: Minimal Flet Launcher

## Goal

Launch a native Flet window from Apmatia's project environment without disturbing the existing Streamlit entry point.

## Scope

Implement:

- a project-local Flet dependency
- one Flet entry module
- application title and basic window configuration
- a temporary diagnostic screen
- logging sufficient to diagnose startup failures
- a documented development command

Do not yet replace `main.py` or remove Streamlit.

## Acceptance criteria

- The client launches from the project environment.
- No global Flet installation is required.
- Source changes can be exercised through the supported Flet development command.
- Existing Apmatia tests still run.
- Streamlit remains available during the migration.

---

# Phase 2: Login Journey — First Vertical Slice

## Goal

Render and complete the existing Apmatia login workflow through the Flet client.

## End-to-end flow

```text
Start Flet client
    ↓
Resolve initial route
    ↓
Unauthenticated client requests login view document
    ↓
Generic renderer builds the login controls
    ↓
User enters credentials and activates Login
    ↓
Client emits the existing login intent
    ↓
Apmatia Core authenticates the user
    ↓
Failure: show an error without losing entered username
Success: establish authenticated client state
    ↓
Navigate to a protected placeholder screen
```

## Minimum component support

Implement only the portable components required by the actual login view, expected to include some subset of:

- `page`
- `panel` or `card`
- `text`
- `field:text`
- `field:password`
- `actions`
- `notice`

Do not assume this list is exact; inspect the real login document first.

## Minimum effect support

Implement only the effects required by the real journey, expected to include some subset of:

- `set_state`
- `clear_state`
- `navigate`
- `show_notification`
- `refresh_view`

## Renderer requirements

The renderer must:

- dispatch by portable component type
- preserve component identifiers
- bind field values to adapter-managed state
- convert button or submit events into portable intents
- map validation and authentication failures into visible UI
- raise a clear adapter error for unsupported component types
- avoid importing authentication-module internals into generic renderer code

## Authentication-state requirements

Define an abstraction for authenticated client state before choosing the Flet storage implementation.

The abstraction must distinguish:

- ephemeral form/event state
- state retained while the current view is active
- state retained across navigation during the client session
- sensitive authentication material
- server-owned session state

Do not store passwords.

Do not place long-lived authentication secrets in ordinary preferences storage. Determine whether Apmatia uses cookies, bearer tokens, another session mechanism, or a secure platform service, then use the appropriate client behavior.

## Temporary authenticated route

After successful login, navigate to a minimal protected route such as `/home` containing:

- authenticated username or identity summary
- a clear indication that the Flet authentication slice succeeded
- a Logout action

This is a diagnostic destination, not the final dashboard.

## Logout

Logout must:

- invoke the existing server-side logout behavior when applicable
- clear client authentication state
- clear sensitive stored material
- navigate back to the login route
- prevent the protected placeholder from remaining accessible

## Acceptance criteria

### Successful login

- The real portable login document is rendered.
- Valid credentials are accepted by Apmatia Core.
- Authentication state survives navigation to the placeholder route.
- The protected route identifies the authenticated user.

### Failed login

- Invalid credentials produce a visible error.
- The password field is cleared or handled according to the existing security behavior.
- The username may remain populated for correction.
- No authenticated state is created.

### Route protection

- Opening a protected route while unauthenticated redirects or navigates to login.
- Logging out makes protected routes inaccessible.
- Back navigation does not reveal a usable authenticated screen after logout.

### Architecture

- Login behavior is not hard-coded into the generic component renderer.
- Apmatia Core remains authoritative for authentication.
- Unsupported view-contract features fail clearly.

### Tests

Add automated coverage for:

- login document rendering
- field-state updates
- login intent payload
- successful authentication
- failed authentication
- protected-route redirection
- session state across navigation
- logout

---

# Phase 3: Authenticated Shell and Module Navigation

## Goal

Replace the temporary authenticated screen with a generic Flet shell that can display the module catalog and navigate among portable views.

## Scope

Implement:

- authenticated application shell
- generic module navigation
- route-to-view resolution
- route history and back behavior
- loading, empty, unauthorized, and error states
- logout in the shell
- theme preference wiring where already supported by Apmatia

## Routing requirements

Use the current supported Flet routing model for the installed version. Treat route state as the source of truth for route-level screens.

The router must:

- distinguish public and protected routes
- rebuild the visible route-level view from route state
- support desktop back behavior
- leave room for Android system-back and gesture behavior
- avoid deprecated navigation helpers

## Acceptance criteria

- An authenticated user can see the module catalog.
- Selecting a module resolves a portable view through the API.
- Refreshing or revisiting a route produces a consistent view.
- Unauthorized routes produce a deliberate result rather than a blank screen.
- Back navigation behaves predictably.
- The shell contains no module-specific branches.

---

# Phase 4: First Simple Production Module

## Goal

Prove that the renderer works beyond authentication by porting one simple, representative production module.

## Module selection criteria

Choose a stable module that exercises several ordinary controls without requiring live streaming. Prefer a module with:

- a collection or table
- a detail panel
- a small form
- one or more actions
- straightforward refresh behavior

Avoid beginning this phase with Discussions or Agent Loops; those belong in later rich-interaction phases.

## Likely component expansion

Add only what the chosen module requires, such as:

- `columns`
- `collection`
- `table`
- `form`
- additional field variants
- `detail`
- `status`
- secondary and destructive actions
- confirmation dialogs

## Acceptance criteria

- One real production workflow works end to end.
- Selection state and form state behave correctly.
- Intents are emitted through the shared adapter path.
- Data refreshes without rebuilding the entire application unnecessarily.
- Component additions are covered by renderer tests.

---

# Phase 5: Discussions — Timeline and Composer

## Goal

Port the Discussions workflow and establish patterns for conversational views.

## Scope

Implement the actual contract features required for:

- discussion navigation
- message timeline
- message cards
- composer
- send action
- loading and failure states
- automatic scrolling behavior
- polling or streaming, according to the existing contract

## Research questions

Verify with the installed Flet version:

- efficient incremental list updates
- auto-scroll behavior when the user is already reading older messages
- keyboard submit behavior on desktop and Android
- multiline composer behavior
- attachment selection, preview, upload, and cancellation if attachments are currently supported
- lifecycle-safe polling or stream cancellation

## Acceptance criteria

- Existing discussions can be opened.
- Messages render in the correct order.
- Sending a message uses the existing intent/API path.
- Duplicate and stale updates are rejected according to the view contract.
- The client does not force-scroll a user who is intentionally reading earlier messages.
- Polling or streaming stops when the view is left.

---

# Phase 6: Agent Loops — Terminal, Progress, and Live Updates

## Goal

Port the Agent Loops workflow and establish safe, efficient handling of append-oriented live output.

## Scope

Implement the actual contract features required for:

- terminal-style output
- progress state
- checklist state
- start and stop actions
- append-only updates
- reconnect or refresh behavior
- stale-event rejection
- lifecycle cleanup

## Research questions

Verify:

- efficient large-list rendering
- whether output virtualization is needed
- batching updates to avoid excessive UI redraws
- text selection and copy behavior
- monospaced typography
- maximum retained lines or log-window strategy
- cancellation when navigating away
- behavior when the app sleeps or resumes on Android

## Acceptance criteria

- Live output can update without freezing the client.
- Output ordering remains correct.
- UI updates are batched when necessary.
- Start, stop, and status actions remain synchronized with Core.
- Leaving the view cleans up client-side polling or stream subscriptions.
- Re-entering the view reconstructs the current server-authoritative state.

---

# Phase 7: Contract Coverage Expansion

## Goal

Implement the remaining portable components based on actual production demand.

Possible components include:

- `stack`
- `tabs`
- `card`
- `navigation`
- `markdown`
- `timeline`
- `message`
- `composer`
- `terminal`
- `progress`
- `checklist`
- `tree`
- `expander`

This is not a mandate to create twenty files. Implement only contract features used by supported production views.

## Component support matrix

Maintain a support matrix with at least:

| Contract feature | Supported | Tested | Used by | Known limitations |
|---|---:|---:|---|---|
| page | yes/no | yes/no | views | notes |
| field:text | yes/no | yes/no | views | notes |
| navigate effect | yes/no | yes/no | views | notes |

The matrix becomes the authoritative migration status rather than counting renderer files.

## Acceptance criteria

- Every production view either renders correctly or is deliberately marked unsupported.
- Unsupported features identify the exact missing contract feature.
- No production view silently drops controls or actions.
- Renderer behavior remains module-neutral.

---

# Phase 8: Linux and Android Client Adaptation

## Goal

Preserve one portable client architecture while allowing platform-specific presentation and interaction adjustments.

## Linux client concerns

- keyboard-first navigation
- desktop window sizing
- clipboard behavior
- file dialogs
- native notifications where appropriate
- Wayland limitations
- desktop entry, icon, and application metadata

## Android client concerns

- touch targets
- responsive layouts
- system-back behavior
- software keyboard behavior
- lifecycle pause and resume
- secure storage availability
- file and image selection
- reduced or adapted views where appropriate

Platform-specific presentation code must not change the portable intent or domain contract.

## Acceptance criteria

- Core workflows are usable on Linux.
- The Android client can authenticate and navigate.
- Platform adaptations are isolated and documented.
- Shared renderer code remains the default path.

---

# Phase 9: Packaging and Release Engineering

## Goal

Produce repeatable Linux and Android artifacts after the source-run client is stable.

## Linux packaging

Use Flet's supported Linux build workflow. Document and automate:

- required Linux build dependencies
- project metadata
- application icon and assets
- version and build number
- output location
- clean builds
- smoke testing of the built artifact

The Linux output should be treated as an application bundle or packaged executable with supporting resources—not assumed to be one statically linked file.

## Android packaging

Document and automate:

- APK build for direct GitHub distribution
- signing configuration
- version code and version name
- supported architectures
- permissions
- upgrade testing

## CI

After local builds are understood, add CI jobs that:

- install locked dependencies
- run tests
- build artifacts on the correct host platform
- attach checksums
- preserve logs on failure

Do not make CI packaging the first place the build is ever attempted.

## Acceptance criteria

- A clean machine can reproduce the documented build.
- Built artifacts start without a developer virtual environment.
- The packaged client can connect to Apmatia Core.
- Version metadata matches the release.
- Release artifacts receive smoke tests before publication.

---

# Phase 10: Parity, Cutover, and Streamlit Removal

## Goal

Make Flet the supported GUI only after the required production journeys pass parity testing.

## Representative journeys

At minimum, test:

- launch client
- login failure
- login success
- logout
- protected-route redirect
- module navigation
- one collection/detail workflow
- one create or edit workflow
- send a discussion message
- start and observe an agent loop
- stop or leave a live-updating view
- restart client and reconnect

## Cutover criteria

Flet may replace Streamlit when:

- required stable modules have supported views
- authentication and logout are reliable
- route and back behavior are reliable
- live-update cleanup is reliable
- Linux packaging is repeatable
- existing portable contracts remain framework-neutral
- documentation describes the new development workflow
- unresolved gaps are explicitly accepted rather than hidden

## Removal sequence

1. Mark the Streamlit shell deprecated.
2. Make Flet the default GUI entry point.
3. Run a release or internal testing period.
4. Remove Streamlit-only dependencies and adapter code.
5. Remove compatibility workarounds that no longer serve another client.
6. Confirm the text adapter and API boundary still function.

Do not remove Streamlit merely because the login screen renders in Flet.

---

## Testing Strategy

### Contract renderer tests

For each supported component and effect, test:

- valid contract input
- missing required values
- unsupported variants
- state binding
- event-to-intent conversion
- visible error behavior

Avoid tests that depend unnecessarily on exact widget-tree internals. Test adapter behavior and contract semantics.

### API client tests

Test:

- successful responses
- authentication failure
- authorization failure
- validation errors
- timeouts
- unavailable Core
- malformed responses
- reconnect behavior

### Journey tests

Favor tests that exercise complete workflows from rendered controls to API calls and resulting navigation or updates.

### Manual platform tests

Maintain concise Linux and Android smoke-test checklists for behavior that automated tests cannot reliably cover.

---

## State Model

Apmatia's portable contract defines four conceptual scopes:

- `event`: transient data for one interaction
- `view`: retained while a view remains active
- `session`: retained across navigation for the active client session
- `server`: authoritative state owned by Core

The Flet adapter must preserve these semantics even if Flet does not provide matching built-in names.

### Adapter rules

- `event` state is cleared after the intent lifecycle completes.
- `view` state is namespaced by route/view identity and disposed when appropriate.
- `session` state is available across navigation for the active client.
- `server` state is read or changed only through Core APIs.
- sensitive authentication material uses an appropriately secure mechanism.
- passwords are never persisted.

The adapter should expose its own small state interface so Flet storage APIs can change without leaking throughout renderer code.

---

## Effects Model

Implement effects as an explicit registry or dispatcher.

Initial effects are likely to include:

- `set_state`
- `clear_state`
- `select_item`
- `navigate`
- `refresh_source`
- `refresh_view`
- `show_notification`
- `open_panel`
- `close_panel`
- `start_polling`
- `stop_polling`
- `download`

Each effect implementation must define:

- required payload
- client-side versus server-side responsibility
- lifecycle behavior
- cancellation behavior where applicable
- error behavior
- tests

Do not model polling as an immortal background task. It must be tied to a view or session lifecycle and cancelled deterministically.

---

## Error Handling

The Flet client must distinguish:

- unsupported contract feature
- invalid view document
- validation failure
- authentication failure
- authorization failure
- Core unavailable
- network timeout
- server error
- stale update
- client implementation defect

User-facing errors should be helpful without exposing secrets or raw tracebacks. Development logs should retain enough structured context to debug the failure.

A blank screen is never an acceptable error state.

---

## Security Requirements

- Never persist plaintext passwords.
- Do not log credentials, tokens, cookies, or sensitive intent payloads.
- Use Core as the authority for authentication and authorization.
- Treat all portable documents and API responses as untrusted input requiring validation.
- Do not infer authorization from the fact that a control is hidden.
- Clear authentication material on logout.
- Verify transport assumptions before enabling remote Core connections.
- Use secure platform storage only after confirming its behavior on both Linux and Android.

---

## Known Unknowns Requiring Research

Research these when the corresponding phase begins:

- current Flet Router versus manual route-stack patterns
- secure storage behavior on Linux and Android
- session-only versus persistent client storage
- lifecycle-safe asynchronous tasks
- polling cancellation and app suspension
- efficient rendering of large collections and logs
- tree controls and nested expansion behavior
- file and image picker behavior
- clipboard support
- notification services
- Android keyboard and back-navigation behavior
- accessibility and keyboard focus
- current packaging prerequisites and output layout

Document the chosen API and installed Flet version when each decision is made.

---

## Immediate Next Task for the Coding Agent

The next task is Phase 0 followed by the narrowest possible implementation of Phases 1 and 2.

The coding agent should:

1. Inspect Apmatia's package-management files and use the existing project-local environment.
2. Inspect the real authentication module, portable login view, intents, API behavior, and tests.
3. Add Flet as a declared dependency without installing it system-wide.
4. Add a minimal Flet entry point without replacing Streamlit.
5. Implement only the generic components and effects required by the real login document.
6. Authenticate against Apmatia Core.
7. Navigate to a minimal protected placeholder.
8. Implement logout.
9. Add journey tests.
10. Report any contract gaps before inventing adapter-specific behavior.

### Definition of done for the first milestone

The first milestone is complete when a developer can run the Flet client from Apmatia's project environment, log in using the existing authentication contract, reach a protected placeholder screen, log out, and verify the behavior through automated tests.

Nothing beyond that is required for the first milestone.
