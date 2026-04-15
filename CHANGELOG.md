# Changelog

All notable changes to Apmatia are documented in this file.

## 0.0.1.4 - Desktop Shell and Golden Layout Foundation

- Added the first desktop shell page at `src/interfaces/web/pages/desktop.html` with:
  - top desktop menu bar (`File`, `Edit`, `View`, `Admin`, `Help`)
  - dedicated Golden Layout root container
  - desktop status footer for shell/runtime feedback
- Vendored Golden Layout locally under:
  - `src/interfaces/web/assets/vendor/golden-layout/`
  - including browser-ready CSS/JS assets, ESM runtime files, and license text
  - removed desktop shell reliance on CDN-hosted Golden Layout assets
- Added root third-party attribution for vendored dependency:
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
  - hid duplicated in-panel component titles inside Golden Layout panels (tab title remains as the single title)
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
