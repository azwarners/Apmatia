# Apmatia

Apmatia (Packs Multiple Agents and Tools Into an Application) is an API-first, self-hosted application for interactive agents. It owns agent configuration, role- and application-specific tools, application-facing orchestration, and adapters to external services.

Apmatia uses a module-first architecture:

- reusable capability code should live in modules
- foundational primitives required before module bootstrap should live in core
- new feature work should generally start as a module when it fits the problem
- bundled modules live in `src/apmatia/modules/`
- draft and agent-assisted modules live in `~/.apmatia/workspace/modules/`

The target architecture and the phased realignment plan are documented in
[`docs/architecture/APMATIA_REALIGNMENT.md`](docs/architecture/APMATIA_REALIGNMENT.md).

## What It Is

Apmatia is designed to make AI features feel like application features instead of isolated scripts.

Its architecture enforces a single path:

```text
Interface -> API (internal) -> Core/Module -> External Service
```

That gives the project a few important properties:

- business logic lives in focused modules under `src/apmatia/modules/`
- interfaces stay thin and do not call core directly
- the CLI, HTTP API, and Streamlit UI all share the same behavior

## Current Interfaces

- FastAPI core service on a configurable host and port
- Streamlit UI on a configurable host and port
- CLI entrypoint in `src/apmatia/interfaces/cli/main.py`

## Current Capabilities

- agent management and configuration
- role- and application-specific agent tools
- API-mediated orchestration and external-service adapters
- user, group, and session-backed authentication flows
- shared settings and persistence infrastructure
- registry-driven module metadata, scaffolding, validation, and workspace editing
- stable-only module activation by default, with an explicit all-modules development toggle
- module-driven Streamlit navigation, visibility controls, and generic view rendering
- schema-inferred module view forms for list/create module pages

## Project Structure

```text
src/
└── apmatia/
    ├── api/
    │   ├── http/        # FastAPI transport layer
    │   └── internal/    # canonical application interface
    ├── core/            # shared primitives, orchestration, and runtime wiring
    │   └── modules/     # module scaffolding, planning, validation, workspace tools
    ├── interfaces/
    │   ├── cli/
    │   └── streamlit/
    └── modules/         # bundled feature modules
```

The most important rule is simple: interfaces use the API, and only the API talks to the core.

Modules are the home for feature and infrastructure packages. They own their implementation details and register actions, tools, commands, views, and module metadata. Shared primitives that cannot participate in module activation live in core.

## Modules and Core

Bundled modules in `src/apmatia/modules/` include agents, agent configuration, agent tools, persistence, users, and the Ysparr/IPE adapters. Modules may be stable infrastructure or activatable features, but each owns its domain implementation. The realignment document records modules that are retained, reduced, or archived.

The core package in `src/apmatia/core/` owns application-wide primitives such as `ApmatiaObject` and permission checks, plus configuration, module bootstrap, registry, and runtime orchestration. These facilities are always available and are not controlled by module activation.

## Configuration

Persistent runtime configuration lives in:

```text
~/.config/apmatia/config.json
```

Environment variables can still act as bootstrap defaults, but the config file is the main runtime source of truth.

Settings saved through the API and Streamlit UI include:

- backend selection
- model URL and provider model name
- API key for OpenAI-compatible providers
- max response size
- default system prompt
- UI theme and typography preferences
- server transport security policy, bind host, port, and TLS material

## Running Apmatia

### Start the core API

```bash
./start.sh core
```

This starts the FastAPI service using the configured transport-security policy.

### Start the Streamlit interface

```bash
./start.sh streamlit
```

This starts the Streamlit interface using the configured transport-security policy.

During development, `./start.sh dev` starts both the core service and the Streamlit app locally.

See [docs/TRANSPORT_SECURITY.md](docs/TRANSPORT_SECURITY.md) for the deployment profiles that control when HTTP is allowed and how HTTPS is configured.

## CLI Usage

Install Apmatia's CLI from the repository into an isolated application environment:

```bash
sudo apt install pipx
pipx ensurepath
pipx install --editable /home/nick/ServerData/repos/apmatia
```

Open a new shell after `ensurepath`, then run the CLI from any directory while the Apmatia API is
running:

```bash
apmatia --help
```

The CLI builds its module command tree from the active application registry through the API.
Root, module, resource, and command help are generated automatically:

```bash
apmatia --help
apmatia agents --help
apmatia agents create --help
apmatia ai-model-manager models --help
```

Authenticate once before executing protected commands; the CLI stores the API session token in a
permission-restricted file under the Apmatia configuration directory:

```bash
apmatia login nick
apmatia whoami
apmatia agents list
apmatia agents create --name Planner
apmatia logout
```

Schema-backed commands receive generated flags. Every dynamic command also accepts a JSON object
for uncommon or newly added fields:

```bash
apmatia agents create --name Planner --payload '{"tool_ids":[1,2]}'
```

`apmatia commands` lists the complete active catalog. Development-module commands appear only
when development modules are enabled in Apmatia.

The CLI connects to `http://127.0.0.1:8000/api` by default. Point it at another Apmatia API with
`APMATIA_API_URL`, for example:

```bash
APMATIA_API_URL=http://apmatia-host:8000/api apmatia commands
```

After pulling CLI changes, refresh the editable installation if its package metadata changed:

```bash
pipx reinstall apmatia
```

## Testing

Run the test suite with:

```bash
./test.sh
```

## Versioning and Release Notes

- version file: `docs/VERSION`
- changelog: `docs/CHANGELOG.md`
- HTTP version probe: `GET /api/version`

Version `0.0.1.7` records the module view adapter, schema inference, and the first module-driven
product flow.

## API Notes

The FastAPI layer remains the transport-facing API surface. The Streamlit app stays on the interface side of the boundary and uses the same API contract rather than reaching into core logic directly.

## Module Development

For module creation, planning, validation, workspace editing, and inspection, use the core module helpers and the CLI `module` commands. The workspace path is intentionally separate from bundled modules so draft work can stay isolated until it is ready to be promoted.

Module authors now have a clearer path for UI:

- define the module's models and registry metadata
- describe field intent once through the module view schema helpers
- let the Streamlit adapter render list views and create forms automatically
- use module management visibility to hide modules or specific views from the left navigation

Every module declares first-class `author`, `status`, `category`, `default_enabled`, and `tags` values in both its manifest and runtime registry metadata. Status is deliberately limited to `stable` and `development`; new and uncertain modules stay development until they are ready for ordinary users. The manifest `[metadata]` table is reserved for module-specific extensions.

The application starts in stable-only mode. Development modules remain discoverable but are not activated: their registry contributions, views, dedicated API behavior, providers, and background services stay unavailable. The Module Manager view can explicitly enable all modules for development work through the persisted `ui.show_development_modules` setting.

## Additional Documentation

- architecture: [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md)
- realignment and coupling risks: [`docs/architecture/APMATIA_REALIGNMENT.md`](docs/architecture/APMATIA_REALIGNMENT.md)
- transport security: [`docs/architecture/TRANSPORT_SECURITY.md`](docs/architecture/TRANSPORT_SECURITY.md)
- module creation guide: [`docs/CREATING_MODULES.md`](docs/CREATING_MODULES.md)
- changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)
- third-party notices: [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md)
