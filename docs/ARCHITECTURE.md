# Architecture

Apmatia is built around a strict, API-first layered architecture. Business logic lives in focused modules, foundational primitives and orchestration live in core, the application layer stays thin, and every interface reaches the system through the API boundary.

## Core Principle

All functionality flows in one direction:

```text
Modules/Core -> API (internal) -> Interfaces
```

No layer is allowed to bypass another.

## Execution Flow

All interactive usage follows the same path:

```text
Interface -> API (internal) -> Core/Module -> External Service
```

For HTTP callers, the transport layer sits in front of the same internal contract:

```text
HTTP -> API (http) -> API (internal) -> Core/Module
```

This keeps behavior consistent across the CLI, the FastAPI surface, and the Streamlit application.

## Layers

### 1. Modules (Business Logic and Feature Packages)

**Location:** `src/apmatia/modules/` for bundled modules, `workspace/modules/` for draft modules

Modules contain Apmatia's domain behavior. They implement features, encapsulate persistence details, integrate with model backends, and register application metadata, actions, tools, commands, and views.

They do not know about Streamlit or the CLI and should not own transport concerns.

The stable `persistence` infrastructure module owns shared SQLite document storage, JSON/YAML configuration persistence, persistence descriptors, and structured log-file storage. Other bundled modules declare it as a module dependency and import its APIs from `apmatia.modules.persistence`.

The stable `users` infrastructure module owns authentication plus the user, group, and membership domain. Its registry-backed Users view is the Streamlit management surface, while HTTP and internal API routes use the same module runtime, managers, and repositories.

Module rules:

- bundled modules ship under `src/apmatia/modules/`
- draft, agent-assisted, or user-created work stays in `workspace/modules/`
- modules may depend on other declared modules and core helpers
- modules register capabilities into the registry instead of talking directly to interfaces

#### Module metadata contract

Each module has matching declarative metadata in `manifest.toml` and runtime metadata in `module.py`. Standard fields are first-class:

- `author`
- `status`: `stable` or `development`
- `category`: one of `core`, `infrastructure`, `feature`, `agent`, `tool`, `integration`, `interface`, `development`, or `other`
- `default_enabled`
- immutable `tags`

The manifest `[metadata]` table and the runtime `metadata` dictionary remain available only for module-specific extensions. Standard fields must not be duplicated there. Missing status values are interpreted as `development`, missing categories as `feature`, and missing `default_enabled` values as true. Legacy category and tags values under `[metadata]` are accepted for compatibility, with first-class `[module]` values taking precedence.

#### Activation boundary

Apmatia is stable-only by default. Module bootstrap reads each manifest before importing the module package:

```text
manifest discovery -> maturity/default-enabled filter -> Python import -> registry contributions
```

In stable-only mode, only stable modules with `default_enabled = true` are imported by bootstrap for registration. Development modules remain discoverable through manifest inspection, but their actions, tools, commands, views, providers, dedicated HTTP functionality, and background services are inactive.

The persisted `ui.show_development_modules` setting can switch the application to all-modules mode. The registry-backed Module Manager view exposes it as "Enable all modules." A change rebuilds the active registry and provider set in each process; module deactivation hooks stop background work when returning to stable-only mode.

### 2. Core (Foundation and Orchestration)

**Location:** `src/apmatia/core/`

Core provides primitives that must exist independently of module activation, including shared object ownership and permission checks. It also loads config, bootstraps modules, wires repositories and services together, and applies application-wide rules.

It does not expose interfaces or own transport details.

### 3. API (Internal)

**Location:** `src/apmatia/api/internal/`

This is the canonical programmatic interface for Apmatia. Interfaces and transports use this layer instead of reaching into core or modules directly.

It exposes application capabilities as stable functions and keeps the rest of the system behind a single contract.

### 4. API (HTTP)

**Location:** `src/apmatia/api/http/`

This layer exposes the internal API over FastAPI. It defines routes, request models, response shapes, session requirements, and serialization concerns.

It does not implement business logic or bypass the internal API.

### 5. Interfaces

**Location:** `src/apmatia/interfaces/`

Interfaces are clients of the API boundary.

- `src/apmatia/interfaces/cli/` provides a command-line entrypoint for direct local use.
- `src/apmatia/interfaces/streamlit/` provides the primary interactive UI in Python via Streamlit.

The Streamlit app is organized as a small interface client:

- `app.py` handles layout, auth gating, theme application, custom sidebar navigation, and the shared header menu safeguards.
- `api_client.py` is the interface-side adapter that talks to the FastAPI app contract.
- `pages/` contains focused UI pages for discussion, model management, agent management, login, and settings.

The key architectural point is that the Streamlit interface stays thin. It renders controls and state, but the actual application behavior still flows through the API and then into core and modules.

## Rules

- Application-facing core workflows are only called by the internal API; modules may import foundational models, permission checks, registry contracts, and other documented core helpers.
- Interfaces never call core or modules directly.
- The HTTP layer uses the internal API rather than calling modules directly.

## Configuration Flow

Configuration is loaded from the persistent config store first, with environment variables acting as bootstrap defaults when needed.

```text
config.json (~/.config/apmatia/config.json) -> core/api -> modules/interfaces
                ^
          optional env bootstrap
```

This gives Apmatia persistent local settings without hardcoding secrets into source files.

Model configuration, prompting defaults, and UI preferences are all saved through the same API-controlled configuration path. The Streamlit settings page persists those values through `/api/settings`.

## Discussion Data Lifecycle

Discussion and folder deletion follows a soft-delete lifecycle:

1. Delete actions mark records as trashed with retention metadata.
2. Trashed items disappear from normal discussion and tree views.
3. Restore endpoints can recover items during the retention window.
4. Expired trash is purged automatically after 90 days.

This keeps accidental deletions reversible without cluttering active views.

## Tool Result Persistence

Tool results are displayed back into the discussion flow and are also written to the tool-call audit log, but Apmatia does not maintain a separate durable tool-result store as part of the discussion transcript model.

Practical guidance:

- treat tool outputs as turn-local context unless they are explicitly saved elsewhere
- use memory or wiki tools when a result should survive beyond the current conversation
- use the audit log for debugging and historical inspection of tool calls
- if a workflow needs cross-session retrieval of tool outputs, persist a concise summary into memory or another dedicated store rather than relying on the ephemeral result payload alone

## Extending the System

To add a new feature:

1. Create or extend a module under `src/apmatia/modules/` or `workspace/modules/`.
2. Keep module-specific domain models, services, persistence, and helpers inside that module.
3. Add only genuinely application-wide primitives or orchestration to `src/apmatia/core/`.
4. Expose the capability through `src/apmatia/api/internal/`.
5. Optionally surface it through FastAPI, Streamlit, the CLI, or another interface.

That sequence preserves the API-first boundary and keeps interfaces thin.

## Summary

Apmatia scales by keeping domain logic in focused modules, shared foundations and orchestration in core, and presentation in interface clients. The UI layer remains thin because interfaces consume the API rather than core or modules directly.
