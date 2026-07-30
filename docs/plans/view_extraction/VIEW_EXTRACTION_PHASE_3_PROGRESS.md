# View Extraction Phase 3 Completion

## Status

Phase 3 is complete. Agent Config, Agent Alarms, AI Hosts, Agents, Users and Groups, and Module
Management all route through serialized portable view documents and module commands.

## Completed: Agent Config

Agent Config now uses the Phase 2 contract path:

- `modules/agent_config/views.py` declares `view_contract_ready`.
- Root editing is an item-scoped `edit` action with a portable edit form.
- `modules/agent_config/module_views.py` accepts the generic `item_id` payload.
- `interfaces/streamlit/module_views/renderers.py` no longer dispatches on the Agent Config view ID.
- The Phase 0 hard-coded check and legacy parity references were removed or replaced.
- The complete serialized document snapshot records the reviewed contract change.

## Completed: Agent Alarms

Agent Alarms now declares `agents:list` and `model_configs:list` data sources plus form-field option
bindings in module-owned metadata. Normalization turns those declarations into typed
`ViewDataSource` and `ViewBinding` values. The portable controller projects API results into generic
label/value options, and the contract renderer resolves those options without knowing the alarm
view ID. The view is marked `view_contract_ready`; its Streamlit enrichment call and Phase 0
view-ID allowlist entry are gone. Renderer-neutral document and API projection tests replace the
old enrichment parity test.

## Completed: AI Hosts

Form-scoped SSH preparation actions are promoted to executable top-level contract actions. The
portable controller preserves form drafts, merges returned field values, and renders standard
messages, errors, and shell-command results. Both host views are contract-ready. Resource errors,
troubleshooting guidance, SSH connection tests, key-install commands, and resource probes are
declared as module-owned columns; the legacy renderer no longer infers host troubleshooting from
magic item keys.

## Completed: Agents

The Agents document owns its collection, create/edit fields, full `AgentPrompt` field set, dynamic
model choices, clone action, deletion confirmation, roots, and JSON-backed RAG/tool/metadata fields.
The provider creates and updates prompt records with agents and exposes cloning as a module command.

## Completed: Users and Groups

The Users document describes users, groups, and memberships in one portable collection with unified
create/edit forms and confirmed delete/disable behavior. The provider routes generic commands to
the existing permission-checked user, group, and membership operations. Agent membership choices
come from a declared API data source.

## Completed: Module Management

The Preferences provider exposes activation, modules, and views as flat portable catalog records.
The document declares their columns and update form; the generic update command applies activation,
visibility, and ordering through the existing protected module-management services.

## Completion Gate

Phase 3 is complete only when:

- `ALLOWED_RENDERER_TOKENS` and `ALLOWED_RENDERER_DISPATCH` are empty;
- no management module or view ID remains in `ALLOWED_HARDCODED_VIEW_CHECKS`;
- the Agents, Users, and Preferences management files are absent from the custom-screen allowlist;
- management parity tests exercise serialized documents and API operations;
- the full suite passes and both core and Streamlit are redeployed.

All five conditions are satisfied. The old management render functions remain only as unreferenced
`render_legacy` regression fixtures; production dispatch cannot reach them, and they are not active
custom screens under the architecture test.

## Handoff to Phases 4–6

Do not reopen Phase 3 or restore management renderer tokens. Continue with the expanded Phase 4,
Phase 5, and Phase 6 instructions in `docs/REPLACEABLE_INTERFACE_VIEW_PLAN.md`. In order: extract
Discussion/contacts and Agent Loops rich behavior; replace the module-aware Streamlit shell with
generic catalog/routing/navigation; then prove replaceability with a headless renderer, a minimal
second GUI, Streamlit-blocked/absent tests, and deliberate compatibility cleanup. Each phase now
lists its starting state, exact targets, sequencing constraints, parity evidence, and completion
gate.
