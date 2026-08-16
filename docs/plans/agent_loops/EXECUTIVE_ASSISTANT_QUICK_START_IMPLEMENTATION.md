# Executive Assistant Quick Start — Implementation Plan for GPT-5.6 Luna

## How to use this plan

Implement phases in order. Do not start a later phase before its exit criterion
passes. Preserve the design contract in
`EXECUTIVE_ASSISTANT_QUICK_START_DESIGN.md` and the destination architecture in
`AGENT_LOOPS_FLET_CLIENTS_BLUEPRINT.md`.

Before each phase:

1. inspect `AGENTS.md` and the touched files;
2. preserve unrelated working-tree changes;
3. add focused tests before or alongside the implementation;
4. run `./test.sh` after code changes; and
5. redeploy Core and Streamlit with the repository-required flow after code
   changes, then exercise the relevant Flet path.

## Phase 1 — durable single-agent agentic runtime

### 1.1 Extend domain types

- [ ] In `src/apmatia/modules/agent_loops/models.py`, add the conversation
  lifecycle/event values required by the design: idle, awaiting approval,
  stopped, archived, user message, assistant message, tool awaiting approval,
  tool result/failure, and task archived/stopped.
- [ ] Keep existing enum values and serialization compatible with current task
  JSON fixtures/tests.
- [ ] Extend `AgentLoopTask` only with fields required for a persistent
  single-agent task: current status, next event sequence, and one serializable
  pending `ToolCall` payload. Do not add a tool list, second agent config, or an
  inbox.
- [ ] Extend `src/apmatia/modules/agent_loops/ports.py` with explicit methods
  for create/get/list/update task, append ordered event, list ordered events,
  and startup sequence reconciliation.

**Tests**

- [ ] Add model serialization/deserialization tests for all new statuses and
  event payloads.
- [ ] Verify unknown legacy task payloads still load safely.

### 1.2 Implement SQLite repository subset

- [ ] Add `src/apmatia/modules/agent_loops/sqlite_repositories.py` with
  `LoopTaskTables`, task/event repositories, and `SQLiteLoopTaskBundle` using
  `apmatia.modules.persistence.SQLiteStore`.
- [ ] Resolve the database path as
  `resolve_agent_loop_workspace_root() / "loop_tasks.db"`; add a narrow test
  override seam rather than a second runtime path convention.
- [ ] Allocate event sequences inside repository-owned locking. On startup or
  first task access, reconcile next sequence from the largest persisted event
  sequence for that task.
- [ ] Sort all event reads by sequence. Never use timestamp ordering.
- [ ] Keep `FileAgentLoopTaskRepository` for existing tests/legacy use; do not
  delete it in this work.
- [ ] Wire the default `AgentLoopRuntime` repository to the SQLite bundle.

**Tests**

- [ ] Persist a task and events, recreate the bundle/runtime, and verify the
  same ordered transcript loads.
- [ ] Append events before/after reload and prove strictly increasing sequence.
- [ ] Verify task listing filters archived tasks and selected `agent_id`.

### 1.3 Convert existing executor into a conversation run

- [ ] Add runtime methods to create/list/get/archive task and submit one user
  message.
- [ ] On submission, validate task ownership/status, append `USER_MESSAGE`, set
  running state, and start the existing `AgentLoopRuntime` background thread.
- [ ] Reuse `ToolManagerToolExecutor.list_tools()` for every normal turn. Do not
  accept a tool list from HTTP/Flet.
- [ ] In `AgentLoopExecutor.execute()`, persist `TOOL_REQUESTED` before each
  call and `TOOL_RESULT`/`TOOL_FAILED` after it. Keep sequential model order.
- [ ] Persist a final `ASSISTANT_MESSAGE` and return to idle only when the model
  produces no tool requests.
- [ ] Retain and test existing cancellation, timeout, max-model-turn, and
  max-tool-call paths. Map their outcome to readable terminal events/status.
- [ ] Treat malformed tool-call JSON, a missing tool, validation failure, and a
  provider failure as visible tool outcomes. They must not kill the runner.

**Tests**

- [ ] Normal no-tool response: user event then assistant event, task idle.
- [ ] One assigned deterministic test-tool call then assistant final response.
- [ ] At least two sequential model/tool continuation cycles from one message.
- [ ] Tool failure is supplied to the next model turn and visible in events.
- [ ] Unassigned tool is denied by existing Agent Tools and never executes its
  provider.
- [ ] Invalid/malformed tool request is controlled and visible.
- [ ] Guard exhaustion and Stop leave a readable, non-running task.

### 1.4 Build bounded conversation prompts

- [ ] Extend `YsparrModelExecutor._build_user_prompt()` to read the ordered task
  events and generate explicit User/Assistant/Tool request/Tool result lines.
- [ ] Keep the current selected-agent system prompt and
  `extend_system_prompt_with_tools()` unchanged as the authority for tools.
- [ ] Bound old transcript/tool-result size with an explicit truncation marker.
- [ ] Ensure the active user's message and current tool results are never
  truncated out of their run.

**Phase 1 exit criterion**

An API-level test creates an existing test agent, assigns a harmless deterministic
tool, sends one message requiring two model/tool cycles, restarts the runtime,
and verifies the ordered transcript ends with the final assistant answer.

## Phase 2 — quick-start API and confirmation bridge

### 2.1 Add API-internal operations and routes

- [ ] Extend `src/apmatia/api/internal/agent_loops.py` with narrow wrappers for
  task creation/list/get, message submission, archive, Stop, and decision on a
  pending call.
- [ ] Replace/extend the matching paths in
  `src/apmatia/api/http/routes/agent_loop_routes.py`. Use Pydantic payloads for
  create, message, and approval decision.
- [ ] Require session and active module on every route. Check owner/group access
  in the service/runtime before returning or changing task data.
- [ ] Return ordered final event dictionaries with their sequence on GET task.
- [ ] Return a conflict response for message submission while running/awaiting
  approval; do not silently queue it.

**Tests**

- [ ] API tests cover each route's happy path, unauthenticated request, access
  denial, missing task, invalid payload, and running-task message conflict.
- [ ] GET task response preserves event ordering after a persistence reload.

### 2.2 Add the minimal confirmation adapter

- [ ] When the existing `ToolManager` returns `pending_confirmation`, persist
  the exact `ToolCall` in task state, append `TOOL_AWAITING_APPROVAL`, and stop
  the runner in awaiting-approval state.
- [ ] Implement approve to call the persisted `ToolCall` once with
  `approval_granted=True`, record its actual result, clear pending state, and
  resume the existing continuation loop.
- [ ] Implement deny to append a denied result without provider execution,
  clear state, and resume the continuation loop.
- [ ] Reject approve/deny if no pending call exists or task access fails.
- [ ] Do not modify `ToolManager`, `ToolExecutor`, assignments, confirmation
  flags, or audit policy to make this work.

**Tests**

- [ ] Confirmation-required assigned test tool produces awaiting approval.
- [ ] Approve invokes the existing tool-manager path once and reaches a model
  continuation/final response.
- [ ] Deny invokes no provider and gives the model a denial result.
- [ ] Restart while awaiting approval preserves the exact pending call.

**Phase 2 exit criterion**

Authenticated API integration tests can create a task, drive normal and
confirmation-required deterministic tool flows, Stop safely, archive an idle
task, and reconstruct the transcript after Core restart.

## Phase 3 — shared Flet terminal and Linux host

### 3.1 Build the shared feature first

- [ ] Create `src/apmatia/interfaces/flet/common/agent_loop_terminal/` with a
  small public controller/view entry point, DTOs, event reducer, terminal
  renderer, and theme constants.
- [ ] Add typed Agent Loops methods to
  `src/apmatia/interfaces/flet/common/api_client.py`: list/create/get task,
  send message, Stop, archive, and decide approval.
- [ ] Reducer state must include selected agent/task, events keyed by sequence,
  status, pending approval, and request error. Reapplying an event sequence is
  a no-op.
- [ ] Render the required dark/green feed entries: user, assistant, tool
  requested, tool result, tool failure, awaiting approval, stopped, and error.
- [ ] Add agent/task selector, New Task confirmation, composer/Send, running
  status, Stop, Copy, and Approve/Deny. Disable Send while running.
- [ ] Poll GET task every ~1 second through `page.run_task()` only while running
  or awaiting approval. Stop polling when route/task changes.

**Tests**

- [ ] Event reducer ordering/deduplication and request error state.
- [ ] Renderer test for every event/status and copy value.
- [ ] Send disabled/enabled transitions, approval actions, archive confirmation,
  and polling cancellation.

### 3.2 Integrate Linux as first real host

- [ ] In `src/apmatia/interfaces/flet/linux/shell.py`, route
  `agent_loops.loops.view` to the shared terminal rather than the generic
  portable renderer.
- [ ] Preserve existing authentication, generic module navigation, and the
  current loop-poll cancellation behavior where compatible.
- [ ] Do not import Android code into Linux.

**Tests**

- [ ] Existing Linux login journey still passes.
- [ ] Linux shell test selects an agent, creates/opens task, receives a
  deterministic tool transcript, and renders the final answer.

**Phase 3 exit criterion**

With Core running, Linux Flet completes a conversation with an existing test
agent, visibly shows its assigned deterministic tool request/result, handles an
approval, and displays the final assistant response.

## Phase 4 — Android host and physical-device verification

### 4.1 Add thin Android package and shared storage

- [ ] Create `src/apmatia/interfaces/flet/android/__init__.py`, `main.py`,
  `app.py`, and `configuration.py`.
- [ ] Extract a small platform-safe storage path helper in Flet common. Prefer
  `APMATIA_FLET_SESSION_FILE`; otherwise use `FLET_APP_STORAGE_DATA` when
  present, then the existing Linux config fallback.
- [ ] Update session persistence in common API client to use that helper.
- [ ] Persist editable Android Core endpoint configuration beside the session;
  normalize it through the existing Linux `normalize_core_url()` logic or a
  common equivalent.
- [ ] Implement a compact login/connection screen and settings action. The
  Android app then hosts the same shared terminal controller/view—no duplicated
  task/event/tool logic.

**Tests**

- [ ] Endpoint normalization/persistence and Android storage path selection.
- [ ] Session restore/logout cleanup against a temporary Flet app-data path.
- [ ] Android host wiring exercises the shared controller with the same mocked
  API fixture used by Linux.

### 4.2 Establish only the required build/test path

- [ ] Add minimal `[tool.flet]` application metadata to `pyproject.toml` and
  `usesCleartextTraffic = "true"` under
  `[tool.flet.android.manifest_application]` for trusted LAN/VPN development.
- [ ] Run `uv run flet doctor`; install only reported Android/Flutter tools.
- [ ] Connect one physical USB-debugging Android device and verify `adb devices`.
- [ ] Verify the pinned Flet 0.86.4 build syntax with `uv run flet build --help`.
- [ ] Build a sideload APK using the Android main module and device ABI, install
  it using `adb install -r`, and record the exact successful command in the
  Android package README or implementation note.

**Device acceptance**

- [ ] Enter a LAN/VPN Core URL, log in, reopen the app to verify session restore.
- [ ] Open a task created on Linux and verify the same ordered transcript.
- [ ] Run a deterministic assigned-tool message, including a pending approval,
  and verify the final response.

**Phase 4 exit criterion**

The physical Android device has the same useful Agent Loops conversation as
Linux against one Core: shared task IDs, ordered events, agent selection, Send,
status, Stop, and confirmation controls.

## Phase 5 — executive assistant + OpenIPE acceptance

This phase does not add OpenIPE-specific runtime code to Agent Loops.

- [ ] Confirm the real executive-assistant agent has a working model and can
  complete the deterministic assigned-tool journey first.
- [ ] Give the toolsmith workflow OpenIPE API documentation and the existing
  Apmatia tool provider/definition format.
- [ ] Add/register OpenIPE read and write providers through ordinary Agent
  Tools, then assign them to the executive assistant using the Agents/Tools
  workflow.
- [ ] Ensure providers call OpenIPE's API/service boundary, not its database.
- [ ] Mark the first write tool confirmation-required through its existing tool
  definition or agent assignment when Nick wants that safety gate.
- [ ] Add provider contract tests for actual structured read output and write
  success/failure output.

**Final acceptance, on Linux and Android against the same Core**

- [ ] “What should I work on today?” causes one or more assigned OpenIPE read
  tools, possible repeated model/tool cycles, and a useful truthful answer.
- [ ] “Add ‘finish Apmatia agentic loop’ to my Apmatia project and make it my
  highest-priority task.” triggers the assigned OpenIPE write tool(s), shows
  their actual results, and reports success only when the tool succeeds.
- [ ] Repeat the two workflows from both Linux and the physical Android device.

**Phase 5 exit criterion**

Nick can use the same existing executive-assistant agent for real OpenIPE read
and approved-write productivity work from Linux and Android, with all tool work
visible in the shared server-side transcript.

## Deferred work after quick-start

Do not start these while pursuing the weekend milestone: durable FIFO user
interruptions, acknowledgement turns, multiple active conversations, multi-agent
orchestration, event cursor/long polling/SSE/WebSocket, token persistence,
summarization, Android biometrics/notifications/attachments/polish, and
Internet-facing HTTPS deployment. Extend this implementation when those phases
begin; do not replace its task/event or shared-terminal contracts.
