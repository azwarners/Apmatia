# View Extraction Recovery Plan

## Purpose

This is the execution handoff for recovering the replaceable-interface migration after an
unverified Phase 4–6 implementation pass. It supplements, but does not replace,
`docs/REPLACEABLE_INTERFACE_VIEW_PLAN.md`.

The recovery has two objectives:

1. restore a trustworthy, fully passing application baseline; and
2. complete the original architecture honestly, with each phase proven by its completion gate.

Do not optimize for reducing the failure count. Optimize for making the tests and architecture
tell the truth. A green suite that serializes empty fallback documents or exercises only mocks is
not a successful recovery.

## Non-negotiable repository rules

- Read `AGENTS.md` before changing code.
- Interfaces use Apmatia APIs. They do not import Apmatia core or module implementations.
- Modules do not import GUI frameworks.
- Do not restore module-specific Streamlit screens, module/view-ID dispatch, or semantic session
  keys merely to satisfy obsolete tests.
- Do not delete or weaken tests just because they fail. Classify each failure first, preserve the
  behavior in a renderer-neutral test when it remains required, and explain any obsolete test.
- Preserve Nick's intentional migrations:
  - `contacts_and_discussions` became `discuss`;
  - `module_manager` was merged into `preferences`.
- Preserve unrelated dirty-worktree changes. The checkout is not clean and contains the work from
  all view-extraction phases.
- After code changes, run `./test.sh`, deploy core and Streamlit with
  `env APMATIA_DOCKER_BIND_HOST=0.0.0.0 ./start.sh dev`, and verify ports 8000 and 8501.

## Current verified state

### Last trustworthy pre-handoff baseline

Before the unverified Phase 4–6 pass, Phases 0–3 had reached a full-suite result of 586 passing
tests and both services were deployed successfully.

### First recovery audit baseline

On 2026-07-28, the full `./test.sh` run collected 590 tests:

- 556 passed;
- 34 failed.

The failures were not one defect. They fell into these groups:

1. contract-ready module views declared new presentation, source, state, and action objects in
   metadata, but `normalize_view_document()` ignored those fields and emitted legacy fallback
   documents;
2. Phase 0/architecture inventories did not match the current source;
3. old Streamlit tests still patched or asserted Discussion/Agent Loops helpers that had been
   removed;
4. registry, CLI, contract-ready inventories, and document snapshots did not include the new
   `discuss.discussion.view` consistently;
5. preferences tests still expected the old `metadata["ui"]` representation;
6. the new Phase 6 acceptance tests used a synthetic document and mock API instead of all active
   registered documents and real HTTP/document journeys.

### Diagnostic normalization work already present

Recovery work has begun in:

- `src/apmatia/core/view_contract/normalization.py`;
- `src/apmatia/modules/preferences/views.py`.

The normalizer now attempts to consume first-class `presentation`, `data_sources`, `state`,
`actions`, `effects`, and `refresh_policy` metadata. That exposed previously hidden invalid
documents. The immediate full-suite result became 546 passing and 44 failing because registry
bootstrap began correctly rejecting malformed declarations.

The newly exposed validation errors include:

- table components without their own bindings;
- field components without explicit semantic `properties.key` values;
- duplicate component IDs caused by reusing the same field components in create and edit forms;
- follow-on registry and CLI failures because invalid views stop module registration.

`_prepare_declared_presentation()` currently attempts deterministic shorthand expansion for those
issues. Treat it as provisional diagnostic/recovery code, not automatically as the final design.
Prefer explicit, reviewable module declarations for semantic field keys and stable component IDs.
Do not retain heuristic key inference unless tests prove it is intentional contract behavior and
the contract documentation is updated accordingly.

## What the audit established

### Useful work worth preserving

- a versioned view-contract package exists under `src/apmatia/core/view_contract/`;
- many module view files contain useful proposed presentation trees, sources, state, actions,
  effects, and refresh policies;
- `discuss` and the preferences-based module-management migration are intentional;
- a headless renderer foundation exists;
- a small text-adapter prototype exists;
- migration guidance for a Flet adapter exists;
- many old custom management-renderer branches were removed.

### Claims that are not yet proven

Phase 4 is complete. Discussion/contact semantics and Agent Loops operations now travel through
serialized documents, API-owned sources, and module command providers. The verified live checks
covered authenticated document discovery, Discussion sources, Agent Loops sources, a bounded
Qwen-backed Agent Loop start, running state, stop, and terminal cancellation.

Phase 5 is not complete. The Streamlit shell still contains semantic route keys such as
`selected_page`, `selected_module_id`, and `selected_module_view_id`, plus Discussion/contact
state and module-specific routing/consequences.

Phase 6 is not complete. The headless test does not yet load every active registered document, the
second adapter primarily uses a mock API, and Streamlit-absent packaging/import behavior has not
been proven in the required environment.

The architecture test currently claims zero custom Streamlit screens, and the former Discussion
screen has been removed after portable renderer-neutral coverage was added. Phase 5 and Phase 6
claims remain intentionally unproven.

## Recovery strategy

Execute the stages below in order. Do not resume the original phase sequence until Stage 3 has a
green full suite. Work in small batches and run focused tests after each batch. Run the full suite
at every stage gate.

## Stage 0 — Preserve evidence and establish a reproducible baseline

### Actions

1. Read this plan, the original plan, `VIEW_CONTRACT_V1.md`, and the Phase 0–3 completion notes.
2. Inspect `git status --short` and `git diff --stat`. Do not assume any dirty file is disposable.
3. Run `./test.sh` once before further edits and save the exact failure summary in the work log or
   next progress update.
4. Confirm the two intentional module migrations above; do not restore the old module packages.
5. Classify every failing test as one of:
   - production regression;
   - invalid new contract declaration;
   - stale expectation after an intentional migration;
   - architecture inventory mismatch;
   - snapshot/inventory update requiring semantic review;
   - inadequate or synthetic acceptance coverage.

### Gate

- Every failure has an owner category.
- No test or production path has been removed merely to improve the count.
- The current normalizer behavior and malformed documents are reproduced consistently.

## Stage 1 — Repair the contract foundation and declared documents

This stage has priority over Streamlit test repair because invalid documents make all later results
untrustworthy.

### 1A — Choose and document one declaration shape

Use one explicit path for contract-ready views:

- module view metadata contains first-class contract objects; and
- `normalize_view_document()` constructs the complete `ViewDocument` from those objects.

Legacy `metadata["ui"]` adaptation may remain only for views not yet contract-ready. A view marked
`view_contract_ready` must never silently fall back to the legacy adapter.

Add a regression test that deliberately supplies distinct first-class presentation, sources,
state, actions, effects, and refresh policy and asserts that every field survives normalization and
JSON round-trip serialization.

### 1B — Make every first-class document valid explicitly

Audit at least these module view files because they declare first-class presentation objects:

- `modules/agent_alarms/views.py`
- `modules/agent_config/views.py`
- `modules/agent_loops/views.py`
- `modules/agent_tools/views.py`
- `modules/agents/views.py`
- `modules/ai_host_management/views.py`
- `modules/discuss/views.py`
- `modules/memory_manager/views.py`
- `modules/preferences/views.py`
- `modules/users/views.py`

For every document:

- every field has an explicit semantic `properties.key`;
- every component ID is stable and unique across the entire document;
- create and edit forms use separately identified components even when they share field semantics;
- each collection/table has the binding required by the contract and renderer;
- every component action key resolves to a declared action;
- every action has a real command/API operation and correct scope;
- state/effect targets resolve;
- polling sources declare cursors, generation keys, update semantics, stale rejection, and stop
  conditions where required;
- module metadata contains no Streamlit names, fragment names, widget keys, or session keys.

Do not solve semantic key omissions by permanently guessing field names from component IDs unless
that shorthand becomes an explicitly documented and tested part of contract v1.

### 1C — Prove registry-wide validity

Add or strengthen one registry test that:

1. creates the application registry with development modules included;
2. normalizes every registered view;
3. validates every document;
4. JSON round-trips every document;
5. reports the exact view ID and contract path on failure.

### Gate

- Registry bootstrap succeeds in stable and development modes.
- Every registered document validates and JSON round-trips.
- No contract-ready view takes the legacy fallback path.
- Core registry, CLI module catalog, module-document API, view-contract, and Phase 2/3 focused tests
  pass.
- `./test.sh` no longer has failures caused by invalid view registration.

## Stage 2 — Restore semantic compatibility without restoring Streamlit ownership

### 2A — Reconcile inventories deliberately

Update contract-ready view inventories, registry expectations, CLI expectations, and snapshots only
after inspecting the serialized document content.

Do not blindly regenerate hashes. For each changed snapshot, review at least:

- presentation root and children;
- source keys and operations;
- state definitions;
- action keys, command IDs/operations, and effects;
- refresh behavior and required capabilities.

`discuss.discussion.view` and `discuss.chat_targets.view` must be represented consistently wherever
the active view inventory is asserted.

### 2B — Replace obsolete tests with portable parity tests

Several Streamlit tests still patch removed functions such as Agent Loops live-output helpers or
assert old contacts-shell flags. Do not restore those helpers simply for the tests.

For each stale test:

1. identify the behavior it protected;
2. determine whether the behavior remains required by the original Phase 0 parity baseline;
3. move the assertion to a module document/provider/API/controller/headless test;
4. retain only adapter-level assertions that are genuinely Streamlit-specific, such as widget
   mapping, fragments, reruns, cookie synchronization, CSS, DOM integration, and widget keys;
5. remove or rewrite the stale test only after equivalent portable coverage is present.

Required preserved behaviors include Discussion create/reopen selection, timeline/message shaping,
generation/cursor rejection, Agent Loops start/poll/stop/history/output/checklist behavior, and
preferences/module-catalog updates.

### 2C — Make architecture inventories truthful

Architecture tests are debt inventories, not aspirational declarations.

- Remove an allowlist entry only when the source scan is actually clean.
- Keep `discussion.py` represented while it remains a custom Streamlit screen.
- Record every direct core/module import still present in interfaces; then eliminate it through an
  API boundary rather than approving it permanently.
- The final allowed interface-to-core/module import set should be zero, consistent with
  `AGENTS.md`. Transitional entries require an explanation and removal stage.

### Gate

- Every removed Streamlit-specific behavioral test has renderer-neutral replacement coverage.
- Inventories equal actual scans.
- Snapshots reflect reviewed semantics rather than merely new hashes.
- The full suite passes before Phase 4 extraction resumes.

## Stage 3 — Establish the recovery baseline

Run the complete verification sequence:

```text
./test.sh
env APMATIA_DOCKER_BIND_HOST=0.0.0.0 ./start.sh dev
```

Verify:

- core responds on `0.0.0.0:8000`;
- Streamlit responds on `0.0.0.0:8501`;
- login/register documents load;
- one generic CRUD view loads and executes an action;
- preferences and module management load from portable documents;
- a representative management view loads with dynamic options.

Record exact commands, test count, endpoint results, and any known debt. This becomes the new
trusted baseline.

### Gate

- Full suite green.
- Both services healthy.
- No known document is empty because of fallback normalization.
- Original plan status is updated only to the last gate actually proven.

## Stage 4 — Complete original Phase 4: rich interactive views

Return to the detailed Phase 4 instructions in the original plan. Execute Discussion/contacts and
Agent Loops as separate sub-stages; do not combine them into another broad rewrite.

### 4A — Discuss

- Move contact navigation/filtering and selected contact/discussion state into documents/providers.
- Provider/API decides create versus reopen and returns declared navigation/selection effects.
- Move header/model/timeline/attachment/activity/composer/group-mode/message mutation semantics
  out of Streamlit.
- Preserve cursor/generation tokens, append/replace semantics, stop conditions, and stale rejection.
- Replace participant/chat-target enrichment in `pages/module_views.py` with sources, conditional
  fields, provider consequences, and portable effects.
- Remove `module_views/discussion.py` only when renderer-neutral tests cover the complete required
  behavior and ordinary component rendering provides the UI.

### 4B — Agent Loops

- Document contact selection, Current Task, Task History, Workspace, Knowledge, new-task form,
  live output, execution log, checklist/progress, analysis, stop controls, and trees.
- Move task/checklist shaping behind module/API boundaries.
- Use refresh policies and generation/cursor semantics for polling and terminal output.
- Remove all interface imports of Agent Loops implementation helpers.
- Replace module/view branches only after start, progress, stop, history, output, workspace, and
  knowledge parity tests pass through serialized documents.

### Gate

Use the original Phase 4 gate literally. In addition, run source scans proving no Discussion or
Agent Loops module/view-ID dispatch, helper imports, or module-specific semantic state keys remain
under `interfaces/streamlit/`.

## Stage 5 — Complete original Phase 5: generic shell

- Introduce API-provided navigation catalog and renderer-neutral route records.
- Replace `selected_page`, `selected_module_id`, `selected_module_view_id`, contacts flags, and
  Agent Loops flags with generic route and view-state adapters.
- Remove module IDs, view IDs, domain object types, and module-specific consequences from
  `interfaces/streamlit/app.py` and sidebar/header code.
- Keep authentication gating, theme/browser integration, hidden built-in Streamlit navigation,
  header stacking safeguards, and generic renderer concerns in the adapter.
- Move all remaining interface imports of core/module code behind APIs.

### Gate

- Literal and AST scans find no domain module/view checks in the Streamlit shell.
- Interface dependency scan finds no core/module implementation imports.
- Route restoration, hidden modules/views, contextual navigation, back/exit, authentication
  transitions, and action-driven navigation are covered by tests.
- Full suite and deployment checks pass.

## Stage 6 — Complete original Phase 6: real replaceability proof

### Headless traversal

The acceptance test must load every active registered document, not construct one sample. For each
document, traverse every component, binding, condition, source, state definition, action payload,
effect, navigation target, and refresh policy. Failure output must include view ID and exact path.

### Second adapter

The text adapter may remain deliberately small, but acceptance must use the real HTTP/document
client boundary for representative journeys. Mocks may support unit tests; they cannot be the sole
completion evidence.

Cover authentication, generic collection/form/action, dynamic options, management, Discussion
timeline/composer, Agent Loops start/poll/terminal/stop, navigation, confirmations, and effects.

### Streamlit absence

Test all of the following with Streamlit imports blocked and in an environment where Streamlit is
not installed:

- core bootstrap;
- module registry;
- CLI;
- API;
- catalog discovery;
- document serialization;
- headless traversal;
- text adapter.

If practical, exclude the Streamlit package tree from the import path as a further check.

### Packaging and compatibility cleanup

Only after caller searches prove they are unused, review the compatibility shims and legacy paths
listed in original Phase 6. Remove targets one at a time with focused and full-suite verification.
Do not use deletion as evidence of decoupling; prove decoupling first.

### Gate

Use the original Phase 6 completion gate literally. A synthetic document, mock-only adapter, or
stubbed `sys.modules["streamlit"]` test alone is insufficient.

## Recommended execution batches for Luna

Keep each batch independently reviewable:

1. normalizer contract-preservation regression test and implementation;
2. one module's malformed document declarations plus focused tests;
3. repeat Batch 2 module by module;
4. registry-wide validation and JSON round trip;
5. inventories/CLI/snapshot reconciliation;
6. stale test classification and portable replacement, one behavior family at a time;
7. full-suite/deployment recovery baseline;
8. Discuss extraction;
9. Agent Loops extraction;
10. generic shell;
11. headless all-view traversal;
12. real second-adapter journeys and Streamlit-absent packaging proof;
13. documentation and compatibility cleanup.

At the end of each batch, report:

- files changed;
- behavior moved or repaired;
- focused tests run and result;
- full-suite result when required;
- exact remaining failures or architecture debt;
- whether the current stage gate is satisfied.

## Stop conditions

Stop and report instead of guessing when:

- a proposed change would delete or restore a whole module outside the two confirmed migrations;
- a failing test's protected behavior cannot be identified;
- a snapshot changes without an understood semantic cause;
- fixing a view requires adding framework terminology to module metadata;
- an interface would need to import core/module code;
- a phase gate fails after the implementation batch;
- deployment requires credentials, authority, or destructive action not already authorized.

## Final definition of recovered

Recovery is complete only when all of the following are true:

- `./test.sh` passes;
- every active registered view validates and JSON round-trips;
- every contract-ready view serializes its real presentation, sources, state, actions, effects, and
  refresh behavior without legacy fallback;
- Discussion and Agent Loops operate through documents plus HTTP APIs;
- Streamlit contains no module/view-ID dispatch, module helper imports, module-specific semantic
  state, or domain action consequences;
- the generic shell consumes an API catalog and renderer-neutral routes;
- the headless renderer traverses all active documents;
- the second adapter completes real representative journeys;
- core/modules/API/CLI/text adapter work without Streamlit installed;
- core and Streamlit deploy successfully to ports 8000 and 8501;
- the original plan and completion notes state only what the evidence proves.
