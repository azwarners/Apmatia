# View Extraction Phase 2 Completion

## Outcome

Phase 2 moves public authentication and every current schema-first generic module view from the
legacy Streamlit adapter path to serialized version 1 view documents. Streamlit remains the widget
renderer, but it no longer reconstructs these views from registry metadata or imports the legacy
descriptor and intent models.

## Runtime Boundary

The portable path is:

1. Streamlit discovers a catalog view through the API.
2. A contribution marked `view_contract_ready` is retrieved from
   `GET /api/module-views/{view_id}/document`.
3. Declared `module_view_items:{view_id}` data sources are loaded through the module-view items API.
4. The serialized component tree is rendered by `contract_renderer.py`.
5. Portable intent events are handled by `portable_page.py` and dispatched through module-command
   API calls.
6. Declared success or failure effects update semantic state and request refreshes.

Public login and registration use normalized documents from `GET /api/auth/views`, because those
views must be available before a session exists.

## Migrated Generic Inventory

The executable inventory contains 17 registered views:

- Agent Tools
- five AI Model Executor views
- three AI Model Manager views
- five IPE views
- Application Logs
- Memory Manager
- Worksim Org Chart

These 17 Phase 2 view IDs form the base of the cumulative contract-ready inventory frozen in
`tests/unit/test_phase2_generic_views.py`. Later extraction phases may deliberately add reviewed
views to that exact inventory; a contribution cannot silently enter or leave it.

## Supported Generic Behavior

The Streamlit contract runtime implements:

- version checking and serialized component traversal
- collection and table bindings
- form fields, defaults, initial edit values, and create/edit submission
- view and item intents
- module-command dispatch
- confirmation for destructive item actions
- view-scoped semantic state initialization
- safe nested conditions and data/state/capability bindings
- set, clear, select, notification, panel, polling, and refresh effects
- declared module-view data-source loading
- JSON-safe date, time, datetime, and uploaded-file payloads

## Deferred Views

The following are deliberately not mislabeled as generic:

- Agent Config, Agent Alarms, AI Hosts, Agents, Users and Groups, and Module Management (Phase 3)
- Discussion, contacts, and Agent Loops (Phase 4)

They remain protected by the Phase 0 debt and behavioral-parity inventories. Their compatibility
imports do not form part of the generic renderer path.

## Completion Gate

Phase 2 is complete because:

- generic views fetch normalized documents through the API;
- generic data and commands cross the API boundary;
- the generic renderer and controller contain no compatibility-adapter, descriptor-model, or
  legacy-intent dependency;
- auth uses the same serialized contract before login;
- create, edit, delete, data-source, state, condition, effect, and routing parity is executable;
- the Phase 0 generic parity baseline now references the renderer-neutral tests.
