# Architecture

Apmatia is built around a **strict, API-first layered architecture** designed to enforce a single execution path and prevent logic duplication.

---

## 🧠 Core Principle

All functionality flows in one direction:

```
Libraries → Core → API (internal) → Interfaces
```

No layer is allowed to bypass another.

---

## 🔁 Execution Flow

All interactions follow the same path:

```
Interface → API (internal) → Core → Library → External Service (LLM)
```

For HTTP requests:

```
HTTP → API (http) → API (internal) → Core → Library
```

This ensures:

- consistent behavior across all interfaces

- no duplicated logic

- easy extensibility

---

## 🧱 Layers

### 1. Libraries (Business Logic)

**Location:** `src/libraries/`

Libraries contain all real functionality.

They:

- implement features

- contain domain logic

- integrate with external systems (e.g., KoboldCpp via ysparr)

- are completely independent of the rest of the system

They do NOT:

- know about APIs

- know about HTTP

- know about CLI or UI

> Libraries should be reusable outside of Apmatia.

---

### 2. Core (Orchestration)

**Location:** `src/core/`

Core coordinates libraries.

It:

- calls one or more libraries

- composes and transforms results

- defines application-level behavior

It does NOT:

- implement business logic

- expose interfaces

- handle HTTP or CLI concerns

> Core is the orchestrator, not the source of logic.

---

### 3. API (Internal)

**Location:** `src/api/internal/`

This is the **canonical interface** of the system.

Everything that interacts with the application must go through this layer.

It:

- exposes core functionality as simple functions

- provides a stable contract for all interfaces

It does NOT:

- contain business logic

- depend on HTTP

> This is the single source of truth for how the system is used programmatically.

---

### 4. API (HTTP)

**Location:** `src/api/http/`

This layer exposes the internal API over the network using FastAPI.

It:

- defines routes

- handles request/response formatting

- maps HTTP calls to internal API functions

It does NOT:

- call libraries directly

- contain business logic

> HTTP is just a transport layer.

---

### 5. Interfaces (CLI, Web, etc.)

**Location:** `src/interfaces/`

Interfaces are clients of the internal API.

They:

- call `api/internal`

- present results to users

- provide different ways to interact with the system

Examples:

- CLI

- web UI (`index`, `discussion`, `settings`)

- mobile UI

- future game or automation interfaces

They do NOT:

- call core directly

- call libraries directly

- implement business logic

> Interfaces are consumers, not owners.

For the web interface, presentation is split into external assets under `src/interfaces/web/desktop/`:

- HTML entry pages (`index.html`, `discussion.html`, `settings.html`)
- shared stylesheet (`styles.css`)
- page scripts (`discussion.js`, `settings.js`, `theme-runtime.js`)
- reusable Web Components (`ai-settings.js`, `discussion-settings.js`, `theme-settings.js`, `about-info.js`)
- reusable mobile/navigation modules (`mobile-drawer.js`, `folder-browser.js`, `folder-picker.js`)
- interaction helpers (`mobile-menu.js`, `auth-ui.js`)

---

## 🚫 Rules (Strict)

- Core is ONLY called by the internal API

- Libraries are ONLY called by core

- Interfaces NEVER call core or libraries directly

- HTTP NEVER calls core directly

---

## ⚙️ Configuration Flow

Configuration is loaded from a persistent config file first, with environment variables as fallback/bootstrap.

Example:

```
config.json (~/.config/apmatia/config.json) → core/api → libraries/interfaces
               ↑
         optional env bootstrap (.env/container env)
```

This ensures:

- no secrets in source code

- persistent runtime settings across CLI + HTTP + web UI

- portability across systems

The web `/settings` screen persists both model/discussion options and UI preferences (theme, font family, font size) through `/api/settings`.

---

## 🗑️ Discussion Data Lifecycle

Discussion and folder deletion follows a soft-delete lifecycle:

1. Delete action marks records as trashed (`deleted_at`, `purge_after`)
2. Trashed items are excluded from normal tree/discussion views
3. Restore APIs can recover folders/discussions during retention window
4. Expired trash is purged automatically after 90 days

This behavior keeps accidental deletions reversible while preserving clean active views.

---

## 🧠 Design Goals

- **Single execution path**

- **Separation of concerns**

- **Library reusability**

- **Interface consistency**

- **Minimalism over abstraction**

---

## 🏭 Extending the System

To add a new feature:

1. Create or extend a library

2. Add orchestration in core

3. Expose it via the internal API

4. Optionally expose via HTTP or CLI

No existing layers should be modified beyond what is necessary.

---

## 🚧 Future Evolution

Planned architectural additions:

- Model manager (LLM routing and selection)

- Multi-user support

These will extend the system without breaking the existing layering.

---

## 💬 Summary

Apmatia enforces a clean architecture where:

- logic lives in one place

- access is centralized

- interfaces remain thin

- the system scales without becoming tangled
