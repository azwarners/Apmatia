# Architecture

Apmatia is built around a strict, API-first layered architecture. Business logic lives in small libraries, feature packages live in modules, the application layer stays thin, and every interface reaches the system through the API boundary.

## Core Principle

All functionality flows in one direction:

```text
Libraries -> Modules -> Core -> API (internal) -> Interfaces
```

No layer is allowed to bypass another.

## Execution Flow

All interactive usage follows the same path:

```text
Interface -> API (internal) -> Core -> Library -> External Service
```

For HTTP callers, the transport layer sits in front of the same internal contract:

```text
HTTP -> API (http) -> API (internal) -> Core -> Library
```

This keeps behavior consistent across the CLI, the FastAPI surface, and the Streamlit application.

## Layers

### 1. Libraries (Business Logic)

**Location:** `src/apmatia/lib/`

Libraries contain the real domain behavior for Apmatia. They implement features, encapsulate persistence details, integrate with model backends, and stay reusable outside the main application.

They do not know about HTTP, FastAPI, Streamlit, or the CLI.

Top-level libraries in `src/apmatia/lib/` currently include:

- `agent_management`

  Provides the agent domain model, repository interfaces, SQLite-backed repositories, and lifecycle services for creating, updating, listing, and deleting agents. This is the business layer behind the agent management screen and API endpoints.

- `apmatia_core`

  Provides the shared object and permission primitives used across Apmatia. In practice this is the common foundation for UID/GID-style ownership and access checks that other libraries and orchestration code build on.

- `discussions`

  Provides discussion-oriented logic, including prompt construction, discussion templating helpers, and the bridge from a saved discussion state to an LLM request. This is the library that turns a user prompt plus context into an executable model interaction.

- `model_management`

  Provides CRUD behavior for saved LLM configurations. It normalizes model records and persists reusable backend definitions into shared application configuration so discussions and agents can select models consistently.

- `persistence`

  Provides lightweight persistence primitives, especially SQLite-backed storage and logging helpers. This package exists so higher layers can rely on a focused storage library instead of mixing data access details into orchestration code.

- the stable `ysparr` infrastructure module (and the new Seat-based concurrency infrastructure)

  Provides the underlying generative execution engine used by Apmatia to talk to text-generation backends. It supplies modality-specific execution, backend adapters such as KoboldCpp and OpenAI-compatible endpoints, and output persistence for model runs.

### 2. Modules (Feature Packages)

**Location:** `src/apmatia/modules/` for bundled modules, `workspace/modules/` for draft modules

Modules package application features. They register application metadata, actions, tools, commands, and views into the registry. Modules are the preferred place for new feature work when the feature can be isolated cleanly.

The stable `users` infrastructure module owns authentication plus the user, group, and membership
domain. Its registry-backed Users view is the Streamlit management surface, while HTTP and internal
API routes use the same module runtime, managers, and repositories.

Module rules:

- bundled modules ship under `src/apmatia/modules/`
- draft, agent-assisted, or user-created work stays in `workspace/modules/`
- modules may depend on libraries and core helpers, but they should not own transport concerns
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

### 3. Core (Orchestration)

**Location:** `src/apmatia/core/`

Core coordinates one or more libraries into application behavior. It loads config, wires repositories and services together, applies app-specific rules, and shapes library behavior into complete workflows.

It does not expose interfaces or own transport details.

### 4. API (Internal)

**Location:** `src/apmatia/api/internal/`

This is the canonical programmatic interface for Apmatia. Interfaces and transports use this layer instead of reaching into core or libraries directly.

It exposes application capabilities as stable functions and keeps the rest of the system behind a single contract.

### 5. API (HTTP)

**Location:** `src/apmatia/api/http/`

This layer exposes the internal API over FastAPI. It defines routes, request models, response shapes, session requirements, and serialization concerns.

It does not implement business logic or call libraries directly.

### 6. Interfaces

**Location:** `src/apmatia/interfaces/`

Interfaces are clients of the API boundary.

- `src/apmatia/interfaces/cli/` provides a command-line entrypoint for direct local use.
- `src/apmatia/interfaces/streamlit/` provides the primary interactive UI in Python via Streamlit.

The Streamlit app is organized as a small interface client:

- `app.py` handles layout, auth gating, theme application, custom sidebar navigation, and the shared header menu safeguards.
- `api_client.py` is the interface-side adapter that talks to the FastAPI app contract.
- `pages/` contains focused UI pages for discussion, model management, agent management, login, and settings.

The key architectural point is that the Streamlit interface stays thin. It renders controls and state, but the actual application behavior still flows through the API and then into core and libraries.

## Rules

- Core is only called by the internal API.
- Libraries are only called by core.
- Interfaces never call core or libraries directly.
- The HTTP layer never calls libraries directly.

## Configuration Flow

Configuration is loaded from the persistent config store first, with environment variables acting as bootstrap defaults when needed.

```text
config.json (~/.config/apmatia/config.json) -> core/api -> lib/interfaces
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

1. Create or extend a library in `src/apmatia/lib/` if the logic is reusable.
2. Decide whether the feature belongs in a library or a module.
3. Package the feature in a module under `src/apmatia/modules/` or `workspace/modules/`.
4. Add orchestration in `src/apmatia/core/`.
5. Expose it through `src/apmatia/api/internal/`.
6. Optionally surface it through FastAPI, Streamlit, the CLI, or another interface.

That sequence preserves the API-first boundary and keeps interfaces thin.

## Summary

Apmatia scales by keeping logic in focused libraries, feature packages in modules, orchestration in core, and presentation in interface clients. The UI layer remains thin because interfaces consume the API rather than the core directly.
