# Changelog

All notable changes to Apmatia are documented in this file.

## Unreleased - Module Metadata and Stable-Only Activation

- Added first-class module maturity, category, author, default-enabled, and immutable tag metadata to manifests and runtime registry records.
- Limited maturity to `stable` and `development`, with development as the compatibility-safe default for manifests that omit status.
- Migrated bundled manifests under `src/apmatia/modules/` so standardized values live in `[module]` and `[metadata]` remains reserved for extensions.
- Made startup stable-only by default and added the Module Management "Enable all modules" toggle for explicitly activating development modules.
- Changed bootstrap to classify manifests before importing module Python packages, keeping inactive development actions, tools, commands, views, providers, dedicated routes, and background services out of the active application.

## 0.0.1.7 - Module View Adapter and Schema Inference

- Added a generic Streamlit module view adapter under `src/apmatia/interfaces/streamlit/module_views/` so module views can be rendered from opaque registry-backed descriptors instead of handwritten page code.
- Added a minimal, extendible module view schema layer that can infer table columns and create forms from dataclass-backed model fields, with small per-field overrides for labels, visibility, and widget hints.
- Wired the Streamlit shell to use module visibility from the module management API so hidden modules and hidden views disappear from the left navigation.
- Added a generic module-view runtime and API endpoints so Streamlit can list module items and execute module commands through the application boundary instead of calling module internals directly.
- Promoted `ipe` as the first bundled module to use this path for real functionality, including idea capture through the inferred form schema.

## 0.0.1.6 - Modular Architecture and Workspace Modules

- Added the bundled module system under `src/apmatia/modules/` so packaged application features can
  register metadata, commands, views, and actions through a shared application registry.
- Added module creation guidance in `docs/CREATING_MODULES.md` and a richer architecture overview
  that explains where bundled modules fit in the layered design.
- Added workspace-oriented module tooling in the CLI, core, libraries, and tests so module
  planning, scaffolding, validation, and workspace editing can be exercised end to end.
- Updated the documentation and recovery note to make the correct checkout and the module workflow
  harder to miss in future sessions.

## 0.0.1.5 - Streamlit Interface Migration

- Replaced the primary browser-facing Golden Layout HTML/JavaScript interface with a Streamlit-based Python interface under `src/interfaces/streamlit/`.
- Added a Streamlit application shell that keeps authentication, page routing, appearance theming, and the custom header/sidebar behavior in Python.
- Split the interactive UI into focused Streamlit pages for:
  - discussion
  - model management
  - agent management
  - settings
  - login
- Kept the API-first boundary intact during the migration:
  - the Streamlit interface remains a client of the API layer
  - business logic still lives in libraries under `src/lib`
  - orchestration still lives in `src/core`
- Updated documentation to reflect the Streamlit architecture and the current library inventory.

## 0.0.1.4 - Desktop Shell Foundation

- Added the first desktop shell page at `src/interfaces/web/pages/desktop.html` with:
  - top desktop menu bar (`File`, `Edit`, `View`, `Admin`, `Help`)
  - interface root container
  - desktop status footer for shell/runtime feedback
- Added root third-party attribution file:
  - `THIRD_PARTY_NOTICES.md`
- Added initial desktop layout foundation modules:
  - `src/interfaces/web/js/panel-registry.js`
  - `src/interfaces/web/js/panel-permissions.js`
  - `src/interfaces/web/js/layout-manager.js`
- Introduced Linux-style panel metadata and resolution model for desktop UI behavior:
  - owner/group/other permission metadata per panel
  - effective access evaluation in owner -> group -> other order
  - read/write helpers for menu filtering and open checks
- Registered first real Discussion desktop panels and default workspace layout:
  - left: Discussion Tree
  - center: Discussion
  - right top: Participants
  - right bottom: Discussion Settings
- Added permission-aware desktop behavior:
  - View menu lists only readable panels for current user context
  - panel opening path blocks non-readable panels even if invoked outside menu click path
  - opened panel host receives effective access metadata for future read-only/write-aware UI
- Desktop shell polish:
  - fixed View panel menu hide/show behavior so it closes reliably when dismissed
  - moved desktop status text from bottom footer into top menu bar to maximize workspace height
  - hid duplicated in-panel component titles (tab title remains as the single title)
- Refactored Discussion UI toward reusable `apm-*` Web Components for mobile + desktop reuse:
  - `apm-discussion-tree-page`
  - `apm-discussion-page`
  - `apm-discussion-participants-panel`
  - `apm-discussion-settings-panel`
- Added first reusable settings category `apm-*` panel-capable components:
  - `apm-ai-settings-panel`
  - `apm-discussion-settings-category-panel`
  - `apm-theme-settings-panel`
  - `apm-about-panel`
  - wired into mobile settings page and registered for desktop panel use
  - applied initial stricter permission defaults for AI settings

## 0.0.1.3 - Layering and Boundary Enforcement

- Moved reusable user/group logic into library space:
  - `src/core/user_management` moved to `src/lib/user_management`
  - core now owns only app-specific runtime composition in `src/core/user_management_runtime.py`
- Pushed web interface logic down into API/core layers to keep interfaces thin.
- Pushed API-owned orchestration logic down into `src/core` so API remains a transport/contract layer.
- Enforced strict call boundaries across layers:
  - HTTP API routes call only `src/api/internal`
  - internal API calls only `src/core`
  - core is the only layer that calls libraries in `src/lib`
- Updated docs and imports to reflect `src/lib` naming and the new boundaries.

## 0.0.1.2 - Discussion Tree Upgrade

- Reworked Discussion Tree mobile UX from deeply nested indentation to folder-based navigation:
  - fixed folder navigation bar under mobile title bar
  - current-folder browsing (`Root` and parent-step back behavior)
  - subfolders shown first, discussions shown after
- Added reusable folder navigation state module:
  - `src/interfaces/web/webcomponents/folder-browser.js`
- Added reusable hierarchical folder picker module:
  - `src/interfaces/web/webcomponents/folder-picker.js`
  - used for create-folder parent selection and folder moves
- Upgraded folder and discussion list item actions in Discussion Tree:
  - discussion row meatballs fixed and scoped correctly
  - discussion metadata switched from repeated `(private)` to created-on timestamps
  - sharing state moved into row action menu
  - folder rows include meatballs actions (`Rename`, `Move`, `Delete`, `Sharing` placeholder)
- Added reusable mobile drawer Web Component:
  - `src/interfaces/web/webcomponents/mobile-drawer.js`
  - migrated pages to shared drawer config
- Added soft-delete trash model with restore APIs and 90-day retention:
  - folder delete now moves folder subtree and contained discussions to trash
  - restore folder subtree/discussion endpoints
  - trash listing endpoint
- Improved startup/runtime troubleshooting:
  - version file + startup version print
  - `/api/version` endpoint
  - no-cache headers for web assets
  - stronger container recreation in startup scripts

## 0.0.1.1 - Discussion Page Upgrade

- Major mobile-first Discussion page polish:
  - fixed bottom controls for prompt + send + status
  - conversation area fills remaining viewport
  - reliable live-stream scrolling behavior with user-controlled follow mode
- Added `Latest` jump button when user is not at current/bottom point
- Added chat-style message rendering with per-message visual boundaries
- Replaced `User:` display with authenticated first-name label (for example, `Nick:`)
- Improved mobile drawer behavior and tap targets on Discussion page
- Reworked top-right avatar from immediate logout to user action menu
