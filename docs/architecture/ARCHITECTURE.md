# Architecture

Apmatia is an application for interactive agents. Its canonical responsibility is to load an
agent, apply its configuration, expose the tools appropriate to that agent and role, orchestrate
the request, and adapt to external services such as Ysparr.

The target architecture, ownership matrix, phased disposition plan, and known coupling risks live
in [`APMATIA_REALIGNMENT.md`](APMATIA_REALIGNMENT.md). This document defines the stable layering
rules that remain true during that realignment.

## Core Principle

Interactive work follows one application boundary:

```text
Interface -> HTTP/API transport -> API (internal) -> Apmatia-owned modules/core
                                                        -> external adapter -> external service
```

The API is the application-facing contract. Interfaces do not call core or modules directly, and
external-service behavior does not become Apmatia-owned merely because an adapter is hosted here.

## Layers

### 1. Apmatia modules (owned application behavior)

**Location:** `src/apmatia/modules/` for bundled modules, `workspace/modules/` for draft modules

Modules contain Apmatia-owned behavior: agents, agent configuration, agent tools, authentication,
users, preferences, persistence, logging, and application-specific adapters. They register
metadata, actions, tools, commands, and views.

They do not know about Streamlit or the CLI and should not own transport concerns.

The stable `persistence` infrastructure module owns shared SQLite document storage, JSON/YAML
configuration persistence, persistence descriptors, and structured log-file storage. Other bundled
modules declare it as a module dependency and import its APIs from `apmatia.modules.persistence`.

The stable `auth` infrastructure module owns sessions, login orchestration, and the Streamlit login view. The stable `users` infrastructure module owns the user, group, and membership domain and its registry-backed management view. HTTP and internal API routes use the modules' runtime entrypoints.

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

### 2. Core (foundation and application wiring)

**Location:** `src/apmatia/core/`

Core provides primitives that must exist independently of module activation, including shared object
ownership, permission checks, configuration, module bootstrap, registry management, and
application-wide rules. Application workflows belong behind the internal API even when core
coordinates them.

It does not expose interfaces or own transport details.

### 3. API (internal)

**Location:** `src/apmatia/api/internal/`

This is the canonical programmatic interface for Apmatia. It owns application-facing orchestration
and keeps transport and presentation concerns outside the domain modules.

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
- `src/apmatia/interfaces/text/` provides a deliberately small text-based adapter for proving contract replaceability.

The Streamlit app is organized as a small interface client:

- `app.py` handles layout, auth gating, theme application, generic module catalog navigation, and the shared header menu safeguards.
- `api_client.py` is the interface-side adapter that talks to the FastAPI app contract.
- `pages/` contains focused UI pages for discussion, model management, agent management, login, and settings.

The Text adapter provides a second GUI implementation that proves the API/document boundary is framework-neutral:

- `text_adapter.py` implements authentication, generic CRUD/form views, dynamic options, one management view, Discussion timeline/composer behavior, Agent Loops polling/terminal behavior, navigation, confirmations, and action-result effects.

The key architectural point is that interfaces are now demonstrably one of multiple adapters. All interfaces consume the API/document contract rather than core or modules directly. The view contract models in `core/view_contract/` define the portable document boundary that both adapters negotiate.

## External Boundaries

- **Ysparr/proxq:** model execution infrastructure. Apmatia may own a client or adapter contract;
  it does not own execution backends, modalities, runtime persistence, or process management.
- **Redless:** long-running autonomous agent loops. Apmatia may initiate an interactive request;
  durable autonomous scheduling and loop execution belong outside Apmatia.
- **Sidecaravan:** reusable cross-agent capabilities. Apmatia consumes or adapts those capabilities
  when needed for its own agents; it does not become their general-purpose home.
- **OpenIPE and Worksim:** standalone productivity or simulation applications. Apmatia may expose
  agent-facing tools or future adapters, but their application implementations are not Apmatia
  responsibilities.

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

## Extending the System

To add a new feature:

1. Create or extend a module under `src/apmatia/modules/` or `workspace/modules/`.
2. Keep module-specific domain models, services, persistence, and helpers inside that module.
3. Add only genuinely application-wide primitives or orchestration to `src/apmatia/core/`.
4. Expose the capability through `src/apmatia/api/internal/`.
5. Optionally surface it through FastAPI, Streamlit, the CLI, or another interface.

That sequence preserves the API-first boundary and keeps interfaces thin.

## Summary

Apmatia owns the interactive agent application boundary. Keep application behavior in focused
modules, shared foundations and wiring in core, presentation in interface clients, and all
external execution behind explicit adapters.
