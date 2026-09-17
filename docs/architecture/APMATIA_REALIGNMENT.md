# Apmatia Realignment: Target Architecture

This document freezes the target architecture for the realignment described in GitHub issue #1.
It is the Phase 1 reference for Phases 2–6. It records ownership and migration risks; it does not
authorize module deletion by itself.

## Project identity

Apmatia means **Packs Multiple Agents and Tools Into an Application**. It is the application layer
for interactive agents, not a general model-runtime platform or a collection of unrelated
productivity applications.

## Apmatia owns

- interactive agent lifecycle and agent configuration
- role- and application-specific tools and their safe execution boundary
- application-facing orchestration for an interactive request
- authentication, users, preferences, persistence, and logging needed by that application
- adapters and client contracts for external services
- API contracts consumed by CLI, HTTP, and UI interfaces

## Apmatia does not own

| Responsibility | System of record | Apmatia boundary |
| --- | --- | --- |
| Long-running autonomous loops | Redless | request/event adapter only |
| Model execution infrastructure, runtimes, and modalities | Ysparr / proxq | thin client or adapter |
| Reusable cross-agent capabilities | Sidecaravan | consume or adapt selected capabilities |
| Standalone productivity applications | OpenIPE, Worksim, and successors | agent-facing tools or future external adapters |

## Canonical request path

```text
CLI / HTTP client / UI
        |
        v
HTTP transport (when applicable)
        |
        v
Internal API
        |
        +--> authentication and user context
        +--> agent + agent configuration
        +--> role/application tool selection and execution
        +--> application orchestration
                     |
                     v
             external adapter/client
                     |
                     v
                 Ysparr / proxq
                     |
                     v
              response -> API -> interface
```

Interfaces remain replaceable clients. They must not import core or module implementations to
complete a user workflow. The API is the only application boundary that coordinates core, owned
modules, and external adapters.

## Module disposition plan

This is the implementation order, not a request to remove modules during Phase 1.

| Phase | Modules / area | Disposition |
| --- | --- | --- |
| 2 | `agent_loops`, `ai_host_management`, `ai_model_executor`, `dev_tools`, `discuss`, `knowledge_wiki`, `memory_manager`, `os_admin`, `runtime_telemetry`, `worksim` | Archive from the active architecture; repair registrations, routes, providers, and tests first. |
| 3 | `ysparr` | Reduce to an Apmatia-side client/adapter contract. Remove in-process execution, modality, persistence, and backend ownership from Apmatia. |
| 4 | `ipe` | Reduce to OpenIPE-backed agent tools and client schemas; remove the embedded standalone productivity implementation. |
| 5 | `ai_model_manager` | Archive the current GGUF/runtime implementation. Preserve only model/provider/route selection concepts needed by `agent_config`. |
| 6 | docs, tests, and identity | Repair stale references after the implementation reduction is complete. |
| Ongoing | `agent_alarms`, `agent_config`, `agent_tools`, `agents`, `apmatia_admin`, `auth`, `logging`, `persistence`, `preferences`, `users` | Keep as Apmatia-owned application capabilities, subject to the API and activation boundaries. |

## Phase 1 coupling and safety note

The current implementation is not yet at the target boundary. The following coupling must be
resolved before archival work is safe:

1. **API route coupling.** HTTP and internal routes still import discussion, agent-loop,
   AI-host, AI-model-manager, and AI-model-executor implementations directly. Removing a module
   before removing or replacing those routes will break application bootstrap and imports.
2. **Core runtime coupling.** Core runtime helpers still construct model-management,
   memory-management, and wiki services. Tool-management runtime also imports agent-loop,
   development-tool, OS-admin, memory, wiki, and IPE providers. These imports are a registry and
   startup risk even when a module is intended to be inactive.
3. **View-source coupling.** The generic view source layer imports discussion and agent-loop
   models/providers. Streamlit navigation and view loading must be repaired before those modules
   leave the active architecture.
4. **Agent-loop execution coupling.** Agent-loop code currently reaches into Ysparr modalities,
   persistence, agent tools, and agent runtime services. Phase 2 must isolate or archive the loop
   path before Phase 3 changes the Ysparr contract.
5. **Persistence and data-shape coupling.** Several modules share persistence helpers and may have
   durable records in the same application data directory. Archiving code must not silently delete
   or reinterpret existing records; migration or read-only compatibility decisions belong to the
   relevant phase.
6. **Documentation and test coupling.** README claims, module manifests, route tests, registry
   tests, and interface tests still describe the pre-realignment product. They should be updated
   as each implementation phase lands, with Phase 6 performing the final sweep.

### Safe sequencing rule

For each archived module: inventory imports and registry contributions, disable or replace API and
view entrypoints, preserve or migrate durable data, update tests, run the full suite, and only then
remove implementation files. Phase 1 intentionally makes no major code deletion.

## Design decisions frozen by this document

- Apmatia's primary product path is interactive agent use.
- Model execution is an external service boundary, not an Apmatia subsystem.
- Standalone productivity and simulation applications are external products.
- All interfaces use the API; the API coordinates owned modules and adapters.
- The module registry remains useful, but archived modules must not remain active merely because
  they are discoverable.
- Compatibility with superseded architecture is not a reason to retain obsolete behavior after a
  safe migration path exists.

## Phase 2 temporary adapter gaps

- Agent Alarms execution intentionally awaits a Redless adapter; Apmatia does not implement
  autonomous loop execution in this phase.
- LLM/model probing intentionally awaits a Ysparr adapter; model selection and configuration remain
  available, but endpoint probing is not implemented in Apmatia in this phase.

When obsolete persisted configuration is encountered, Apmatia moves it under the internal
`legacy.archived_config` namespace without exposing it through active settings or deleting it.
