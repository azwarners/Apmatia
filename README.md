# Apmatia

Apmatia is an API-first, self-hosted application framework for modular AI workflows. It is built from small Python libraries, keeps orchestration in a thin core layer, and serves both programmatic and interactive use through the same API boundary.

## What It Is

Apmatia is designed to make AI features feel like application features instead of isolated scripts.

Its architecture enforces a single path:

```text
Interface -> API (internal) -> Core -> Library -> External Service
```

That gives the project a few important properties:

- business logic lives in reusable libraries under `src/lib/`
- interfaces stay thin and do not call core directly
- the CLI, HTTP API, and Streamlit UI all share the same behavior

## Current Interfaces

- FastAPI core service on `0.0.0.0:8000`
- Streamlit UI on `0.0.0.0:8501`
- CLI entrypoint in `src/interfaces/cli/main.py`

## Current Capabilities

- discussion workflows backed by reusable libraries
- saved LLM configurations for OpenAI-compatible and KoboldCpp backends
- agent management backed by a dedicated library
- user, group, and session-backed authentication flows
- soft-delete discussion and folder lifecycle with restore support
- shared settings for prompting and UI appearance

## Project Structure

```text
src/
├── api/
│   ├── http/        # FastAPI transport layer
│   └── internal/    # canonical application interface
├── core/            # orchestration and runtime wiring
├── interfaces/
│   ├── cli/
│   └── streamlit/
└── lib/             # reusable business logic libraries
```

The most important rule is simple: interfaces use the API, and only the API talks to the core.

## Libraries

Top-level libraries in `src/lib/` currently include:

- `agent_management` for agent lifecycle operations and persistence contracts
- `apmatia_core` for shared object and permission primitives
- `discussions` for prompt shaping and discussion-oriented model execution
- `model_management` for saved LLM configuration records
- `persistence` for lightweight SQLite-oriented storage helpers
- `user_management` for users, groups, memberships, and authentication
- `ysparr` for backend-agnostic generative execution

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

## Running Apmatia

### Start the core API

```bash
./start.sh core
```

This starts the FastAPI service on `http://127.0.0.1:8000` and publishes it on the LAN.

### Start the Streamlit interface

```bash
./start.sh streamlit
```

This starts the Streamlit interface on `http://127.0.0.1:8501` and publishes it on the LAN.

During development, run both the core service and the Streamlit app locally.

## CLI Usage

```bash
python -m src.interfaces.cli.main "Say hello"
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

Version `0.0.1.5` records the current Streamlit interface rollout.

## API Notes

The FastAPI layer remains the transport-facing API surface. The Streamlit app stays on the interface side of the boundary and uses the same API contract rather than reaching into core logic directly.

## Additional Documentation

- architecture: `docs/ARCHITECTURE.md`
- changelog: `docs/CHANGELOG.md`
- third-party notices: `docs/THIRD_PARTY_NOTICES.md`
