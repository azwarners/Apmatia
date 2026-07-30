# Replaceable Interface View Extraction Plan

## Status

- Document type: architectural migration and implementation plan
- Scope: framework-neutral view descriptions and replaceable graphical interfaces
- Primary interface being decoupled: Streamlit
- Implementation status: Recovery Stages 0–3 are complete; the deployed services are healthy,
  the full suite is green with 593 passed and 0 skipped, and the original Phases 4–6 remain
  incomplete and have not been resumed
- Recovery handoff: `docs/plans/VIEW_EXTRACTION_RECOVERY_PLAN.md`
- Canonical location: `docs/`

This plan lives under `docs/` because it defines a lasting architectural boundary, migration
sequence, and acceptance contract. The existing top-level `plans/` directory contains useful
implementation plans, but this document should remain discoverable alongside the architecture and
module-authoring documentation. Moving or consolidating the older plan files is outside this
plan's scope.

## Executive Summary

Apmatia has already established an important boundary: bundled modules do not import Streamlit,
and module operations are exposed through APIs and registry-backed commands. That prevents the
domain layer from depending on the current GUI framework.

The remaining problem is the opposite dependency. A substantial amount of module-specific view
description, interaction flow, navigation behavior, and presentation state currently exists only
inside `src/apmatia/interfaces/streamlit/`. Removing Streamlit today would therefore remove the
only complete description of several major user experiences, including Discussion, Agent Loops,
Agents, Users and Groups, and Module Management.

The objective of this plan is to make the following operation practical:

1. Remove the Streamlit interface directory.
2. Add a new GUI adapter.
3. Fetch a complete, versioned description of every active view through the API.
4. Render those views without rediscovering their structure or reconstructing their workflows from
   Streamlit code.

Streamlit should ultimately contain only framework integration:

- widget and layout rendering
- translation between framework events and framework-neutral intents
- binding framework-local state to declared view state
- Streamlit-specific styling and browser workarounds
- session and transport integration that is inherently specific to Streamlit

It must not remain the source of truth for module screens, module navigation, domain-specific
forms, related-data loading, action consequences, polling policy, or workflow text.

## Goals

1. Preserve the existing rule that modules never import Streamlit or another GUI framework.
2. Make modules the source of truth for their view semantics.
3. Establish a typed, versioned, serializable view contract that is independent of Streamlit.
4. Expose normalized view documents, data dependencies, actions, and effects through the API.
5. Reduce the Streamlit interface to a generic shell and a component renderer.
6. Preserve all existing user-visible behavior during incremental migration.
7. Allow a second renderer to be developed without importing from `interfaces/streamlit`.
8. Add automated checks that prevent module-specific presentation from drifting back into an
   interface adapter.

## Non-Goals

- Selecting the framework that will eventually replace Streamlit.
- Rewriting working screens before a portable contract exists.
- Moving Streamlit calls into module packages.
- Encoding pixel-perfect CSS, framework widget keys, or browser workarounds in module metadata.
- Forcing every screen into a table-and-form CRUD model.
- Removing dedicated domain APIs when they are the appropriate data or streaming transport.
- Combining business services with presentation specifications.
- Moving the existing top-level `plans/` directory as part of this migration.

## Current State

### Boundaries that are already healthy

- Module packages do not import or call Streamlit.
- View contributions and commands are registry-backed.
- The HTTP API exposes modules, normalized module-view documents, module-view items, and module
  commands.
- The generic adapter can infer basic collection columns and create/edit forms from schema metadata.
- Several modules already declare useful presentation metadata: titles, captions, empty states,
  fields, columns, actions, command IDs, and form text.
- Module view providers own data retrieval and command execution.

These capabilities should be retained and strengthened rather than replaced.

### Presentation that remains stranded in Streamlit

The following files contain complete or partial module experiences rather than only Streamlit
rendering mechanics:

| Current file | Stranded responsibility |
|---|---|
| `interfaces/streamlit/module_views/discussion.py` | Conversation screen, message timeline, streaming activity, composer behavior, attachments, group controls, deletion flows, and contacts-shell content |
| `interfaces/streamlit/module_views/agents.py` | Agent selection, create/edit/clone flow, prompt editing and preview, model selection, directory validation, and deletion state |
| `interfaces/streamlit/module_views/users.py` | User and group tabs, current-account editing, group selection, membership management, and ownership-dependent controls |
| `interfaces/streamlit/module_views/preferences.py` | Module activation, visibility, module order, view visibility, and view order presentation |
| `interfaces/streamlit/pages/module_views.py` | Custom renderer dispatch, generic CRUD controller behavior, participant forms and discussion activation, alarm option enrichment, SSH action results, and the Agent Loops shell |
| `interfaces/streamlit/module_views/renderers.py` | Generic rendering mixed with Agent Config and AI-host troubleshooting special cases |
| `interfaces/streamlit/app.py` | Module-aware contacts and Agent Loops sidebars, module-specific navigation transitions, and direct module/internal integration |

### Portable concepts that are located in the wrong package

The following concepts are not inherently Streamlit-specific but currently live beneath
`interfaces/streamlit/module_views/`:

- collection view descriptors
- column descriptors
- form and form-field descriptors
- action descriptors
- navigation-pane descriptors
- view intents
- view metadata normalization and schema inference

A replacement GUI should not need to import these concepts from a package named `streamlit` or
reimplement them.

### Existing escape hatches

Some module descriptors set a symbolic renderer such as `agents`, `users`, or `preferences`.
Streamlit recognizes the name and dispatches to handwritten Python. A renderer name alone is not a
portable view description: another GUI knows that something special is required, but it does not
know what the screen contains or how it behaves.

Hard-coded checks for module IDs and view IDs have a similar effect. They are evidence that the
portable contract is missing information required to render the view.

## Terminology

To keep responsibilities clear, this plan uses the following terms.

### View contribution

Registry identity and discovery metadata: module ID, view ID, action ID, name, description,
visibility, and the reference to a portable view specification.

### View specification

The module-owned declarative source for what a view means. It describes structure, bindings,
actions, state, effects, and presentation semantics without referencing a GUI toolkit.

### View document

The normalized, versioned, JSON-serializable representation returned through the API. Interfaces
render view documents rather than interpreting arbitrary module dictionaries.

### View model

The data returned for a particular view instance, including records, related option collections,
capabilities, status, and initial state. A view model contains data, not widgets.

### Intent

A framework-neutral user event such as `create`, `save`, `select`, `delete`, `navigate`,
`start_task`, `stop_task`, `send_message`, or `toggle_membership`.

### Effect

A declared result of an intent, such as refresh a data source, update selection, navigate to a
view, open a panel, clear a draft, show a notification, or begin polling.

### Renderer

A framework adapter that maps portable components and intents to concrete widgets and events. The
Streamlit renderer is one renderer; a future desktop, web, or terminal renderer can be another.

## Target Architecture

```text
Module package
  views.py / view_specs.py
    declarative view specifications
  module_views.py
    view-model assembly and command handling
  services.py
    business behavior
          |
          v
Framework-neutral view contract
  typed schema + validation + normalization
          |
          v
Internal API -> HTTP API
  view catalog
  normalized view document
  view model / data sources
  intent or command execution
          |
          +----------------------+----------------------+
          v                      v                      v
  Streamlit renderer       Future GUI renderer     Headless test renderer
```

The dependency direction must remain one-way. Modules know the portable contract but never know a
renderer. Renderers know the portable contract but never import module implementation helpers.

## Proposed Framework-Neutral Contract

The initial contract should be deliberately expressive enough for existing screens. Designing only
for simple CRUD would reproduce the current escape-hatch problem.

### Versioned view document

Every normalized document should include at least:

- `schema_version`
- `view_id`
- `module_id`
- `title`
- `description`
- `presentation`
- `data_sources`
- `state`
- `actions`
- `effects`
- `refresh_policy`
- `capabilities`

The API should reject invalid documents during module registration or registry bootstrap rather
than letting each renderer fail differently.

### Presentation tree

Use a small component tree instead of a single `render_mode` plus custom renderer names. Required
component types should be driven by existing screens:

- `page`
- `stack`
- `columns`
- `tabs`
- `panel`
- `card`
- `collection`
- `table`
- `form`
- `field`
- `text`
- `markdown`
- `status`
- `notice`
- `actions`
- `navigation`
- `detail`
- `timeline`
- `message`
- `composer`
- `terminal`
- `progress`
- `checklist`
- `tree`
- `expander`

Components should describe semantic purpose and relationships. Framework-specific parameters such
as Streamlit form keys, `st.columns` ratios, CSS selectors, or rerun calls must not enter this
contract. Optional presentation hints may express relative emphasis, density, grouping, preferred
width, or responsive priority without requiring a specific toolkit.

### Data sources and bindings

Views need a declarative way to name all data required for rendering. A data source should define:

- a stable source key
- its API resource or module-view query
- required parameters and state bindings
- loading, empty, and error semantics
- whether it is a singleton, collection, stream, or tree
- optional projection and display-label fields
- refresh and cache policy
- dependency on another selection

Examples include:

- agents visible to the current user
- groups and group members
- model aliases used as form options
- tools available to a selected agent
- discussion messages and live activity
- loop tasks belonging to a selected contact
- module and view catalog entries

Dynamic select options must come from declared data-source bindings. Streamlit-specific enrichment
functions should disappear.

### State

Declare durable view state separately from renderer-local widget state. The contract should support:

- selected record or contact
- selected tab
- open create/edit panel
- confirmation target
- form draft
- active discussion or task
- filtering and search values
- polling-active state
- pagination or cursor state

Each state key should declare its type, default, persistence scope, and reset conditions. Suggested
scopes are:

- `event`: exists only while handling one intent
- `view`: retained while the view instance remains active
- `session`: retained across navigation during a user session
- `server`: persisted by an API or module service

Renderer widget identities remain renderer-owned; semantic state identities belong to the view.

### Actions and intents

Actions should declare:

- stable key and intent
- label and optional help text
- scope: view, item, selection, form, message, or navigation
- required capability or visibility condition
- payload bindings
- confirmation policy
- command or API operation
- success and failure effects
- whether duplicate submission must be prevented

The contract must support more than CRUD. Existing required actions include:

- clone an agent
- activate a chat target
- create or reopen a discussion
- send, stop, edit, and delete discussion messages
- start and stop a loop task
- toggle module and view visibility
- reorder modules and views
- toggle group membership
- prepare an SSH key
- inspect host resources

### Effects and navigation

Avoid embedding `st.session_state` changes and `st.rerun()` calls in module workflows. Declare
effects such as:

- `refresh_source`
- `refresh_view`
- `set_state`
- `clear_state`
- `select_item`
- `navigate`
- `open_panel`
- `close_panel`
- `show_notification`
- `start_polling`
- `stop_polling`
- `download`

Navigation should target stable view IDs and optional route parameters rather than Streamlit page
names. A renderer decides how that navigation appears in its own routing system.

### Conditional presentation and capabilities

Views such as Users and Discussion change available controls based on ownership, current identity,
selected target type, running state, or available related records. Conditions should be expressed
against view-model capabilities and state, for example:

- `can_edit_current_user`
- `owns_group`
- `can_manage_membership`
- `discussion_is_running`
- `target_kind == group`
- `task_can_stop`

Do not reproduce authorization rules in the GUI. The API or module provider supplies capabilities;
the view document declares how those capabilities affect presentation.

### Live and streaming behavior

Discussion and Agent Loops require an explicit portable refresh model. It should support:

- interval polling with a declared minimum interval
- stop conditions
- generation or cursor tokens
- append-only event streams
- replacement snapshots
- optimistic and pending action states
- interruption and cancellation actions
- stale-response rejection

The contract describes when and why data changes. Streamlit fragments, empty placeholders, and
reruns remain implementation details of the Streamlit renderer.

### Extension policy

The contract may support versioned extension components, but extensions must not silently become
new custom-renderer escape hatches.

An extension is acceptable only when:

1. Its behavior is documented independently of a framework.
2. Its input and emitted intents are serializable.
3. At least the headless renderer can validate it.
4. Unsupported renderers can report a precise capability error.
5. It is promoted into the common contract if more than one module needs it.

Strings such as `renderer: agents` are not acceptable final-state extensions.

## Proposed Code Placement

Exact names may change during implementation, but the ownership boundary should follow this shape:

```text
src/apmatia/core/view_contract/
  __init__.py
  models.py          # Typed, framework-neutral document and component models
  validation.py      # Contract validation and supported-version checks
  normalization.py   # Schema inference and metadata-to-document conversion
  conditions.py      # Safe condition model, not arbitrary Python evaluation
  effects.py         # Intent result/effect definitions

src/apmatia/api/internal/views.py
  catalog and normalized document access
  view-model loading
  intent execution orchestration

src/apmatia/api/http/routes/view_routes.py
  serialized view documents
  serialized view models/data sources
  action/intent endpoint if required

src/apmatia/modules/<module>/views.py
  view contributions and portable specifications

src/apmatia/modules/<module>/module_views.py
  module-owned view-model assembly and command dispatch

src/apmatia/interfaces/streamlit/view_renderer/
  renderer.py
  components.py
  state.py
  effects.py
  shell.py
```

If the contract must be available before module bootstrap, it belongs in `core`. It must not become
an activatable module. The API remains the only boundary consumed by interfaces.

## Extraction Rules

Use these rules while classifying existing Streamlit code.

### Move into module view specifications

- titles, captions, labels, help text, and empty-state text
- screen, tab, section, panel, and collection hierarchy
- column and field definitions
- semantic component types
- action availability and confirmation descriptions
- data-source declarations and bindings
- default semantic state and reset rules
- navigation targets and action effects
- polling and live-update policies
- domain-specific status presentation rules

### Move into module view providers or services

- assembling related records needed by a view
- calculating capability flags
- deriving stable display fields from domain data
- resolving dynamic options
- validation and normalization of command payloads
- finding or creating a domain object such as a discussion
- parsing domain-specific task or checklist data
- command result semantics

Services continue to own business rules. Providers may assemble view models but must not duplicate
business decisions.

### Move into the framework-neutral contract layer

- descriptor dataclasses currently under the Streamlit package
- schema-to-form and schema-to-column inference
- action normalization
- condition, binding, state, navigation, and effect models
- view-document validation
- compatibility and version handling

### Keep in Streamlit

- `st.*` calls
- Streamlit widget and form keys
- mapping semantic components to Streamlit controls
- Streamlit session-state storage adapter
- rerun and fragment mechanics
- Streamlit page configuration
- CSS and DOM workarounds
- clipboard bridges and other browser integration required by Streamlit
- visual fallbacks for unsupported portable components

### Remove instead of move

- hard-coded module and view dispatch once the contract describes the difference
- duplicated labels already supplied by module specifications
- interface-side domain parsing
- renderer-name escape hatches after their view specifications are complete
- direct imports from module implementation packages

## Implementation Workstreams

### Workstream 1: Contract foundation

Completion note: the foundation exists under `src/apmatia/core/view_contract/`. It owns contract
version 1 models, a test-backed legacy field inventory, semantic components including the rich and
live-update shapes required by Discussion and Agent Loops, strict validation, renderer/version
capability negotiation, legacy metadata normalization, and the compatibility render model.
Registry registration validates normalized compatibility documents. Representative Discussion and
Agent Loops documents validate and negotiate in the test suite. The former Streamlit model and
adapter modules remain temporary re-export shims for later renderer migration.

1. Inventory every field currently accepted by the Streamlit adapter.
2. Define contract version 1 with typed models for collections, forms, actions, state, conditions,
   data sources, navigation, and effects.
3. Include the richer components needed by Discussion and Agent Loops before declaring version 1
   complete.
4. Move or reimplement the current descriptor models and normalization logic in the neutral layer.
5. Preserve temporary compatibility with existing `metadata.ui` dictionaries.
6. Add validation during registry construction.
7. Return actionable validation paths such as
   `views[discuss.chat_targets.view].presentation.children[2].binding`.
8. Define schema-version negotiation and unsupported-version errors.

Deliverable: a normalized view document can be constructed and serialized without importing any
interface package.

### Workstream 2: API surface

1. Add an endpoint to fetch the normalized document for a view.
2. Decide whether view model data is returned with the document or through declared data-source
   endpoints. Prefer separate data when it changes frequently.
3. Ensure all view dependencies are reachable through HTTP rather than Python imports.
4. Expose capability flags and authenticated-user context required for conditional presentation.
5. Standardize command or intent results so effects do not depend on parsing arbitrary messages.
6. Add cursor/generation support for live views.
7. Document error, loading, partial-data, and permission response shapes.

Deliverable: a remote GUI can discover and operate views using only the HTTP API.

### Workstream 3: Generic Streamlit renderer

1. Make Streamlit consume normalized API documents rather than importing the neutral adapter.
2. Implement portable components one at a time behind a component dispatch table.
3. Add a framework-state adapter for declared view and session state.
4. Add a generic intent dispatcher and effect executor.
5. Keep rendering functions free of module and view ID checks.
6. Produce precise unsupported-component diagnostics during migration.
7. Preserve theme, shell, clipboard, and other legitimate Streamlit-specific behavior.

Deliverable: the generic CRUD and form views render with no behavior change from a neutral API
document.

### Workstream 4: Module-by-module extraction

Migrate complete vertical slices. For each view, move its description, view-model assembly, actions,
effects, and tests together before deleting the old custom branch.

#### Discussion and contacts shell

Highest priority because it contains the largest and most stateful stranded experience.

Extract:

- contacts master navigation
- agent/group contact representation
- active contact and active discussion state
- conversation header and model summary
- message timeline and message metadata
- attachment presentation
- live generation activity
- composer and image input semantics
- group-chat mode, pause, resume, and stop actions
- edit, individual delete, and bulk delete workflows
- create-or-reopen discussion transition
- polling, cursor, and stale-response behavior

Module provider responsibilities:

- build the contact and discussion view models
- resolve the active participant and visible agents/groups
- expose message and live-activity records in a stable shape
- execute or delegate discussion commands
- return navigation/effect-relevant result fields

Exit gate: `discussion.py` contains only portable-component-to-Streamlit rendering helpers, or is
deleted because the generic renderer covers the view.

#### Agent Loops

Extract:

- contact navigation and selection
- Current Task, Task History, Workspace, and Knowledge tabs
- new-task form and participant selection
- live output and execution log
- task progress, checklist, summary, and executive analysis
- task-history cards and stop controls
- workspace and knowledge trees
- refresh and terminal append behavior

Move checklist parsing and task presentation shaping behind the module/API boundary. The Streamlit
page must stop importing Agent Loops helpers.

Exit gate: the Streamlit shell contains no `agent_loops` module-ID branch and no Agent Loops state
keys.

#### Agents

Extract:

- create/edit form schema
- agent selection
- clone intent and clone-prefill effect
- prompt selection, editing, and compiled preview
- model options
- ownership inputs and capability rules
- workspace/knowledge validation presentation
- delete confirmation and post-delete selection behavior

Exit gate: remove `renderer: agents` and the dedicated renderer dispatch.

#### Users and Groups

Extract:

- Users and Groups tabs
- current-account panel
- create-user form
- group create/edit and selected-group detail
- membership collection and membership toggles
- ownership-based visibility and capability conditions
- account-deletion logout/navigation effects

Exit gate: remove `renderer: users` and the dedicated renderer dispatch.

#### Module Management

Extract:

- development-module activation control
- module visibility and ordering controls
- nested view visibility and ordering controls
- disabled-state and boundary conditions for move actions
- refresh effects after registry-changing commands

This view is a strong test of nested collections and item actions. It should not remain a custom
preferences renderer.

Exit gate: remove `renderer: preferences` from the module-catalog view.

#### Agent Config

Extract the selected-agent detail form, path-status presentation, save action, and result notices.
Remove the `agent_config.agent_config.view` special case from the generic renderer.

#### Agent Alarms

Replace Streamlit-side agent and model option enrichment with declared data sources. Keep date and
time components portable and perform timezone/domain normalization through the provider or command.

#### Discuss chat targets

Replace participant-view detection and custom target forms with declared conditional fields,
dynamic data sources, and navigation effects. Creating a target may navigate to or activate a
discussion, but that consequence must be declared or returned by the action result.

#### AI Hosts and resource inspection

Describe resource inspection, SSH preparation, troubleshooting records, code/command blocks, and
notices as portable actions and components. Remove host-specific result inspection from the generic
renderer.

#### Remaining schema-first modules

Revalidate IPE, worksim, logging, memory management, agent tools, AI model management, AI model
execution, auth, and the preferences form against the versioned contract. These modules should be
early compatibility fixtures because they are closest to the target design.

### Workstream 5: Shell and navigation

1. Define a portable navigation catalog from visible modules and views.
2. Add support for a view to declare contextual/master-detail navigation.
3. Replace `selected_page`, module-specific shell flags, and special sidebar branches with stable
   route and state models.
4. Preserve renderer-owned choices such as whether contextual navigation appears as a sidebar,
   drawer, tree, or split pane.
5. Keep authentication gating separate from module view semantics while continuing to use the auth
   module's portable login and registration documents.
6. Ensure header actions navigate by stable view ID.

Exit gate: the Streamlit application shell knows about authentication, themes, the view catalog,
and portable navigation, but contains no branches for Discussion, Contacts, Agent Loops, Agents,
Users, or Preferences.

### Workstream 6: Dependency cleanup

1. Remove direct Streamlit-interface imports of module implementation helpers.
2. Route onboarding and other application actions through the HTTP-facing interface client.
3. Move logging access to a legitimate interface/API abstraction if the Streamlit client needs it.
4. Separate generic HTTP client behavior from Streamlit cookie and browser integration so another
   Python GUI can reuse transport code without importing Streamlit.
5. Keep Streamlit cookie synchronization in a small Streamlit-only authentication adapter.

Exit gate: deleting or not installing Streamlit does not prevent importing the core, APIs, portable
view contract, modules, CLI, or a second GUI adapter.

### Workstream 7: Documentation and module-author guidance

Update the following documentation as the contract stabilizes:

- `docs/ARCHITECTURE.md`
- `docs/CREATING_MODULES.md`
- `docs/STREAMLIT_MODULE_VIEWS.md`
- README architecture and extension guidance

Replace Streamlit-centric wording with renderer-neutral terminology. The Streamlit document should
eventually explain only how Streamlit implements the common contract.

Provide at least three examples:

1. simple collection and create form
2. master/detail view with dynamic options and conditional actions
3. live view with timeline, polling, and cancellation

## Migration Sequence

### Phase 0: Freeze accidental coupling

Completion note: exact AST-based allowlists now freeze hard-coded module/view comparisons,
renderer tokens and dispatch, handwritten Streamlit module screens, Streamlit page files, and
direct interface dependency exceptions. Module packages are checked for GUI-framework imports.
The behavioral parity inventory is validated against real test functions, including focused
Discussion characterization tests. See `docs/VIEW_EXTRACTION_PHASE_0_BASELINE.md`.

- Add a temporary inventory test for known hard-coded module/view checks in Streamlit.
- Require new module UI work to use portable metadata.
- Prohibit new renderer-name escape hatches.
- Record current behavior with focused tests before extraction.

Completion gate: no new custom Streamlit module screen is added while the contract is being built.

### Phase 1: Introduce contract version 1

- Add neutral typed models, validation, and normalization.
- Support existing collection and form metadata through a compatibility normalizer.
- Move descriptor and intent types out of the Streamlit namespace.
- Serialize normalized documents through the API.

Completion gate: existing generic views can be inspected and snapshot-tested without importing
Streamlit.

Completion note: the authenticated API now exposes both the active document catalog and individual
normalized documents. A subprocess regression test blocks all Streamlit imports, bootstraps every
bundled module (including development modules), serializes all registered documents through the
internal API, and compares deterministic full-document SHA-256 snapshots. Testing every registered
view is intentionally stronger than testing only the current generic subset.

### Phase 2: Render existing generic views from the new contract

- Point Streamlit's generic renderer at API view documents.
- Implement state, intent, effect, condition, and data-source handling needed by generic views.
- Migrate auth and schema-first modules first.

Completion gate: generic views no longer depend on the old Streamlit adapter models.

Completion note: public authentication and all 17 schema-first generic module views now render from
serialized version 1 documents. The Streamlit API client retrieves documents and declared module
view data sources through HTTP API operations. The contract runtime owns semantic state,
bindings, conditions, effects, generic forms and collections, CRUD intents, confirmation, and
success/failure handling. Generic rendering code imports neither the compatibility adapter nor its
descriptor or intent models. An exhaustive registry inventory and renderer-neutral create, edit,
delete, data-source, condition, state, effect, and API-routing tests enforce the completion gate.
The temporary framework-neutral `view_contract_ready` contribution marker distinguishes migrated
schema-first views from the management and rich-interaction views intentionally deferred to Phases
3 and 4. See `docs/VIEW_EXTRACTION_PHASE_2.md`.

### Phase 3: Extract custom management views

- Agent Config
- Agent Alarms
- AI Hosts
- Agents
- Users and Groups
- Module Management

Completion gate: no custom renderer tokens and no management-view ID checks remain in Streamlit.

Completion note: Agent Config, Agent Alarms, AI Hosts, Agents, Users and Groups, and Module
Management are complete. Agent Config's per-agent workspace and
knowledge-root editing is declared as a portable item action and edit form. Agent Alarms declares
agent/model option data sources and field bindings that normalize into the versioned document; the
portable API controller projects those sources into renderer-neutral options. Both views route
through the Phase 2 API-document controller, and their Streamlit view-ID dispatch/enrichment code
has been removed. AI Hosts executes form-scoped SSH actions through portable actions, preserves
draft/result state, and declares resource troubleshooting content in its document instead of the
Streamlit collection renderer. Agents now declares its editor, prompt fields, model source, clone,
and CRUD actions. Users declares unified user/group/membership workflows. Module Management exposes
activation, module, and view rows with portable update actions. All management renderer tokens,
dispatch branches, and active custom management screens have been removed from the architecture
allowlists.
Continuation details are recorded in `docs/VIEW_EXTRACTION_PHASE_3_PROGRESS.md`.

### Phase 4: Extract rich interactive views

**Starting state:** Phases 0–3 are complete. Generic forms, collections, dynamic option sources,
form actions, result notices, confirmations, state, conditions, effects, and the portable API
document route already exist. Do not reopen management-view migration or restore renderer tokens.
The remaining intentional rich-view debt is frozen by `test_interface_view_architecture.py` and the
`discussion_and_contacts` / `agent_loops` entries in `test_view_extraction_parity_baseline.py`.

**4A — Discussion, contacts, and chat targets:**

1. Start from `modules/discuss/views.py`, `modules/discuss/module_views.py`, and the serialized rich
   component types already defined in contract v1 (`navigation`, `timeline`, `message`, `composer`,
   `detail`, and related state/effects).
2. Move contact navigation, selected contact/discussion state, conversation header, model summary,
   timeline metadata, attachments, generation activity, composer/image semantics, group mode,
   pause/resume/stop, message edit/delete, bulk deletion, and create-or-reopen consequences into
   module documents, providers, API operations, capabilities, and portable effects.
3. Replace the participant/chat-target enrichment still in
   `interfaces/streamlit/pages/module_views.py` with declared sources, conditional fields, and a
   navigation/selection result. The provider—not Streamlit—must decide whether a discussion is
   created or reopened.
4. Preserve cursor/generation tokens, polling stop conditions, stale-response rejection, and
   append/replace semantics. Streamlit fragments, placeholders, and reruns remain adapter details.
5. Remove `interfaces/streamlit/module_views/discussion.py` from the custom-screen allowlist only
   after renderer-neutral parity covers the timeline, active streaming message, contact filtering,
   and agent/group create-or-reopen journeys.

**4B — Agent Loops:**

1. Describe contact selection; Current Task, Task History, Workspace, and Knowledge panels; the
   new-task form; live output; execution log; progress/checklist; summary/executive analysis;
   history cards; stop controls; and workspace/knowledge trees in the portable document.
2. Move checklist parsing and task presentation shaping behind the module/API boundary. Remove the
   remaining Streamlit imports of `agent_loops.prompt_helpers` and `agent_loops.state` only after
   equivalent provider fields and API operations exist.
3. Use contract refresh policies for polling, generation keys for stale-response rejection, append
   semantics for terminal output, and explicit stop conditions. Do not encode Streamlit fragment
   names or session-state keys in module metadata.
4. Remove the `agent_loops` branches in `interfaces/streamlit/app.py` and
   `interfaces/streamlit/pages/module_views.py` only after task start, live progress, history,
   transcript/output, stop, workspace, and knowledge parity tests use serialized documents.

**Phase 4 completion gate:** Discussion/contacts and Agent Loops are discoverable, loadable, and
operable through documents plus HTTP APIs alone. Streamlit renders them through ordinary component
implementations; no module/view-ID dispatch, module helper import, or module-specific state key
remains in the interface. Remove the corresponding Phase 0 allowlist and parity-baseline debt,
review document snapshots, run `./test.sh`, redeploy both services, and verify representative live
flows without weakening cursor/stale-response assertions.

### Phase 5: Replace the shell

**Starting state:** begin only after Phase 4 removes Discussion and Agent Loops special routing.
The shell may know about authentication, theme/browser integration, the visible catalog, routes,
and generic contextual navigation. It may not know module IDs, view IDs, domain object types, or
module-specific action consequences.

1. Define a serialized navigation catalog from the API's visible modules and views, using stable
   route records rather than Streamlit page filenames or display labels.
2. Introduce renderer-neutral route state for the selected module/view and optional contextual
   selection. Preserve back/exit behavior through declared navigation targets and effects.
3. Replace `selected_page`, `selected_module_id`, `selected_module_view_id`, discussion/contact
   flags, Agent Loops shell flags, and similar semantic Streamlit session keys with a generic route
   and view-state adapter. Widget keys may remain Streamlit-specific.
4. Replace module-specific sidebar/header branches in `interfaces/streamlit/app.py` with catalog and
   contextual-navigation component rendering. Keep the built-in Streamlit multipage navigation
   hidden and preserve the existing header stacking and browser-integration safeguards in
   `AGENTS.md`.
5. Route create/open/select/exit/logout and other consequences through declared effects or generic
   shell intents. Domain commands return stable route/effect fields; the shell must not parse
   arbitrary success messages to decide where to go.
6. Separate generic HTTP client/session behavior from Streamlit cookie and browser synchronization.
   Authentication gating remains a shell concern, but login/register content continues to come
   from the auth module's serialized documents.

**Phase 5 completion gate:** a literal/module-ID scan finds no domain module or view checks in the
Streamlit shell. The shell imports no module implementation helpers and contains only generic
authentication, catalog, routing, theme, browser, and component-renderer concerns. Navigation tests
must cover direct route restoration, hidden modules/views, contextual navigation, back/exit,
authentication transitions, and action-driven navigation before old session flags are removed.
Run the full suite, redeploy both services, and update architecture debt inventories to zero for
shell-specific exceptions.

### Phase 6: Prove replaceability

**Starting state:** all production views and shell navigation must already consume the versioned
contract. Phase 6 proves the boundary and performs cleanup; it must not invent missing view
semantics or paper over unsupported components.

1. Build a framework-free headless renderer/validator that loads every active document and walks
   every component, source, binding, condition, state definition, action payload, navigation target,
   effect, and refresh policy. It must report precise contract paths for missing or unsupported
   behavior and never import an interface package.
2. Build a deliberately small second GUI adapter using only HTTP/document APIs. Cover at minimum:
   authentication, a generic CRUD/form view, dynamic options, one management view, Discussion
   timeline/composer behavior, Agent Loops polling/terminal behavior, navigation, confirmations,
   and action-result effects. Visual parity with Streamlit is not required; semantic operation is.
3. Execute the replaceability acceptance test below with Streamlit imports blocked. Then test a
   build/environment where Streamlit is not installed and, if practical, temporarily exclude the
   Streamlit package tree from the import path. Core bootstrap, CLI, API, catalog discovery,
   document serialization, headless traversal, and the second adapter must still work.
4. Remove compatibility-only paths after proving they have no production callers: the
   `module_views/adapter.py` and `module_views/models.py` re-export shims, legacy normalizer fields
   that are no longer emitted, `render_legacy` management fixtures, legacy page/controller code,
   obsolete architecture allowlists, and superseded Streamlit-only parity tests. Delete each target
   deliberately; do not remove compatibility code merely because a new adapter exists.
5. Tighten dependency/package tests so installing core/API/CLI or the second adapter does not pull
   in Streamlit. Keep Streamlit cookie synchronization, CSS/DOM workarounds, clipboard integration,
   page configuration, and widget state entirely inside the Streamlit adapter.
6. Update `ARCHITECTURE.md`, module-author documentation, Streamlit adapter documentation, and the
   README to describe the final API/document boundary and how a new renderer negotiates contract
   capabilities.

**Phase 6 completion gate:** the headless traversal passes for every active view; the second GUI
executes the representative journeys; Streamlit-blocked and Streamlit-absent import/deletion tests
pass; core/modules/API/CLI have no Streamlit dependency; and removing the Streamlit adapter leaves
all portable documents and domain behavior intact. At that point Streamlit is demonstrably one
adapter rather than an architectural dependency. Record exact commands and evidence, run the full
suite, and avoid declaring completion based only on existing Streamlit tests.

## Testing Strategy

### Contract unit tests

- valid documents normalize deterministically
- invalid documents fail with precise paths
- all condition and binding references resolve
- every action references a known command or API operation
- every effect is supported by the declared contract version
- component IDs and state keys are stable and unique within a view
- JSON round trips preserve meaning

### Module contract tests

For every registered view:

- fetch and validate its normalized document
- load its initial view model
- verify all declared data sources are resolvable
- verify all action payload bindings can be constructed
- verify referenced commands belong to an active module
- verify capability and conditional references exist
- verify no framework-specific values appear in the document

### Headless renderer tests

The headless renderer should traverse every active view without Streamlit and report:

- unsupported components
- missing data bindings
- unreachable actions
- invalid navigation targets
- invalid state transitions
- unsupported extensions

This is the primary architectural test. A passing Streamlit test alone does not prove
replaceability.

### Streamlit adapter tests

- each portable component maps to the expected Streamlit primitive
- framework events emit the correct portable intents
- portable effects update Streamlit-local state correctly
- reruns and fragments do not change domain semantics
- unsupported components fail visibly and precisely
- CSS and browser workarounds remain isolated

### Behavioral parity tests

Before removing each custom renderer, test representative workflows against both the old and new
paths. Compare API calls, payloads, resulting navigation/state, and user-visible messages rather
than exact widget implementation.

Required parity journeys include:

- login and registration
- create, edit, clone, and delete an agent
- edit the current user and manage a group membership
- show, hide, enable, and reorder modules/views
- create a chat target and enter its discussion
- send and stop a discussion prompt
- edit and delete discussion messages
- launch, observe, and stop an Agent Loops task
- create and edit an alarm with dynamic agent/model options
- prepare an SSH key and inspect host resources

### Architecture tests

Add automated checks that:

- module packages do not import GUI frameworks
- interface packages do not import module implementation packages or core directly
- portable view-contract packages do not import an interface
- Streamlit renderer files contain no known module IDs or view IDs
- modules do not declare renderer names tied to one interface
- a process can import and enumerate all view documents while imports of `streamlit` are blocked

### Full verification

Each implementation change must follow repository guidance:

1. Run focused tests during development.
2. Run `./test.sh` after the code change is complete.
3. Redeploy both core and Streamlit locally.
4. Verify affected flows through the LAN deployment.

Documentation-only changes do not require deployment.

## Replaceability Acceptance Test

The final architectural acceptance test is intentionally stronger than normal unit coverage.

In an environment where importing Streamlit fails:

1. Import the portable view contract.
2. Bootstrap all active modules.
3. Enumerate the visible module and view catalog.
4. Fetch every normalized view document.
5. Load representative view models for every data-source shape.
6. Traverse every document using the headless renderer.
7. Validate every component, binding, state key, condition, action, effect, and navigation target.
8. Execute representative intents through the API using test repositories.
9. Confirm that the CLI and API import without Streamlit.
10. Confirm that no code outside the Streamlit adapter imports from
    `apmatia.interfaces.streamlit`.

The test passes only if deleting `src/apmatia/interfaces/streamlit/` would remove a renderer, not the
only description of a user experience.

## Compatibility and Rollout

### Dual-path migration

Use a temporary compatibility normalizer for existing `metadata.ui` dictionaries. Do not perform a
single large rewrite.

For each migrated view:

1. Add the portable specification.
2. Expose the normalized document and view model.
3. Render it through the new Streamlit path behind a development flag if needed.
4. Run parity tests.
5. Make the new path default.
6. Remove the old module-specific branch.
7. Remove the flag after one stable release or an explicitly agreed migration window.

### Contract versioning

- Begin with integer schema versions.
- Add fields compatibly within a version only when old renderers can safely ignore them.
- Increment the version for semantic or structural incompatibility.
- Renderers must declare supported versions and component capabilities.
- The API must return a precise incompatibility error rather than silently degrading actions.

### Failure behavior

During migration, unsupported components should render a diagnostic panel containing the view ID,
component type, contract version, and remediation hint. Silent omission is unacceptable for actions
or stateful components.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Designing another CRUD-only schema | Include Discussion and Agent Loops requirements in contract version 1 |
| Turning the contract into arbitrary untyped dictionaries | Use typed models, registry-time validation, and serialized snapshots |
| Recreating authorization logic in clients | Return capability flags from providers/APIs and enforce authorization server-side |
| Moving business logic into view specifications | Limit specifications to presentation semantics; keep validation and operations in services/providers |
| Building a framework-neutral contract that mirrors Streamlit | Name semantic components and test them with a headless and second renderer |
| Unbounded condition language | Use a small typed condition tree; prohibit arbitrary Python or expression evaluation |
| Excessive network chatter from many data sources | Permit batched view-model responses and declared cache/refresh policies |
| Polling differences cause stale updates | Use generation/cursor tokens and explicit stop conditions |
| Large, risky rewrite of Discussion | Migrate view model, timeline, composer, and effects as separately testable slices |
| Compatibility layer becomes permanent | Track every compatibility branch and assign a removal phase/gate |
| Renderer extensions become new escape hatches | Require framework-neutral semantics, headless validation, and promotion rules |
| User-visible regressions | Maintain behavioral parity journeys and deploy after each completed code slice |

## Work Tracking Template

Use the following checklist for each migrated view:

- [ ] Current Streamlit behavior inventoried
- [ ] Module-owned portable view specification added
- [ ] View document validates and serializes
- [ ] All data sources exposed through API
- [ ] Dynamic options declared
- [ ] Capability conditions supplied server-side
- [ ] Actions and payload bindings declared
- [ ] Success, failure, refresh, state, and navigation effects declared
- [ ] Live refresh or streaming behavior declared, if applicable
- [ ] Headless renderer passes
- [ ] New Streamlit renderer path passes focused tests
- [ ] Behavioral parity journey passes
- [ ] Direct module imports removed from the interface
- [ ] Module/view ID checks removed from Streamlit
- [ ] Custom renderer token removed
- [ ] Old code path deleted only after parity is demonstrated
- [ ] Full test suite passes
- [ ] Core and Streamlit redeployed and manually verified
- [ ] Documentation updated

## Milestones

### Milestone A: Neutral contract available

- contract models and validation exist outside all interfaces
- normalized documents are API-accessible
- generic collection and form views pass headless validation

### Milestone B: Management views portable

- Agents, Users and Groups, Module Management, Agent Config, alarms, and host workflows have no
  custom Streamlit dispatch
- all dynamic related-data options are declared

### Milestone C: Rich views portable

- Discussion and Agent Loops are fully described through portable components, state, data, intents,
  effects, and refresh policies
- module-specific shell branches are gone

### Milestone D: Renderer replacement proven

- every active view passes the headless renderer
- a minimal second GUI renders at least one simple form, one management view, and one live view
- blocking Streamlit imports does not affect the API, modules, CLI, view enumeration, or second GUI

## Definition of Done

This migration is complete when all of the following are true:

1. No module imports Streamlit or another GUI framework.
2. No framework-neutral view type or normalizer lives under an interface package.
3. Every visible view has a validated, versioned, serializable document.
4. Every view can obtain all required data through declared API-accessible sources.
5. Every action, condition, state transition, effect, and navigation target is described outside
   Streamlit.
6. Streamlit contains no module IDs, view IDs, custom module renderer dispatch, or module helper
   imports.
7. The Streamlit shell contains no module-specific navigation behavior.
8. Discussion and Agent Loops live behavior is portable and covered by headless tests.
9. A second renderer can start from the same documents without reading Streamlit source.
10. Removing the Streamlit directory removes only the Streamlit implementation and styling, not
    the canonical description of any user experience.

## Recommended First Implementation Slice

The first slice should prove the architecture without beginning with the hardest screen:

1. Create the framework-neutral contract models and move collection/form normalization into them.
2. Expose one normalized document endpoint.
3. Migrate the existing Preferences form or an IPE collection to the new API document.
4. Render it through the new generic Streamlit renderer.
5. Add the headless traversal test.
6. Block Streamlit imports while running that view-contract test.

Once this slice works, migrate Agent Config to prove selected-record state and dynamic detail forms,
then Module Management to prove nested collections and action effects. Begin Discussion only after
the contract has demonstrated those capabilities, but use Discussion requirements to evaluate every
contract decision from the beginning.
