# Executive Assistant Quick Start Blueprint

## Objective

Deliver the smallest production-quality vertical slice that lets Nick use an
existing Apmatia executive-assistant agent from both Linux and Android Flet
clients this weekend. The agent must use the tools already assigned to it
through the normal Apmatia tool system, complete repeated model/tool cycles,
and show the entire useful exchange to the user.

The long-term destination remains
`/home/nick/ServerData/repos/apmatia/docs/plans/AGENT_LOOPS_FLET_CLIENTS_BLUEPRINT.md`.
This document narrows its first implementation slice; it does not alter its
authority boundaries or replace its later architecture.

## The useful moment

1. Nick opens either Flet client, selects an existing agent, and opens the same
   server-side task conversation from either platform when desired.
2. Nick creates or opens a task conversation for that agent and sends: “What
   should I work on today?”
3. Core resolves the agent's already-assigned tools, calls the model, executes
   any requested OpenIPE read tools through `ToolManager`, gives their results
   back to the model, and eventually displays a useful final answer.
4. Nick can send a write request. If its OpenIPE tool is confirmation-required,
   the terminal shows the requested action and arguments, and Nick can approve
   or deny it. The agent reports only the result returned by the tool.

OpenIPE is merely the first serious tool set. The primitive being implemented is
**existing Apmatia agent + its assigned tools + a server-side agentic loop**.

## Non-negotiable authority boundaries

- `modules.agents` remains authoritative for identity, system prompt, selected
  model, and tool assignments.
- `core.tool_management_runtime.get_tool_manager()` and `ToolManager` remain
  authoritative for effective tool availability, validation, execution,
  confirmation-required policy, and tool-call auditing.
- `modules.agent_loops` owns task conversation persistence and orchestration.
- Core executes tools. Linux and Android Flet only render API responses and
  submit user actions.
- Agent Loops receives an `agent_id`; it must never accept or store an
  independently supplied tool list, tool assignment, OpenIPE credential, or
  direct OpenIPE database access.

## Existing components Luna must reuse

| Existing component | Reuse in quick-start |
| --- | --- |
| `src/apmatia/modules/agent_loops/executor.py` `AgentLoopExecutor` | Keep its repeated model-turn / tool-turn loop, limit checks, cancellation checks, `ToolRequest` parsing, and event emission pattern. Extend it for conversation events; do not build a second execution loop. |
| `src/apmatia/modules/agent_loops/service.py` `AgentLoopRuntime`, `YsparrModelExecutor`, `ToolManagerToolExecutor` | Keep the background-runner, selected-agent model resolution, prompt construction, and tool-manager adapter. |
| `src/apmatia/modules/agent_loops/models.py` | Extend the existing task/event models and enums rather than introducing parallel conversation models. |
| `src/apmatia/modules/agent_loops/ports.py` | Extend `AgentLoopTaskRepository` for persistent event reads and task lookup; preserve the repository boundary. |
| `src/apmatia/core/tool_management_runtime.py` and `modules/agent_tools/manager.py` | Resolve current effective tools with `list_tools_available_to_agent(agent_id)` and execute with `execute_tool_call`. |
| `src/apmatia/modules/agent_tools/executor.py` | Preserve its assigned-tool enforcement, schema validation, `pending_confirmation` result, and audit recording. |
| `src/apmatia/api/http/routes/agent_loop_routes.py` | Extend the existing authenticated, module-gated API router. |
| `src/apmatia/interfaces/flet/common/api_client.py` and `src/apmatia/interfaces/flet/common/state.py` | Add shared Agent Loops API DTOs/operations and platform-safe persisted client state. |
| `src/apmatia/interfaces/flet/linux/shell.py` | Host the shared terminal from the existing desktop navigation shell. |
| `src/apmatia/interfaces/flet/android/` | This does not exist yet. Add only a thin Android entry point, app shell, and configuration adapter around the shared terminal. |

## Small persistence subset

Implement a new SQLite database at the Agent Loops workspace root:

`<agent-loops-workspace>/loop_tasks.db`

Use the persistence module's `SQLiteStore`, as the long-term blueprint directs.
Create `SQLiteLoopTaskBundle` in
`src/apmatia/modules/agent_loops/sqlite_repositories.py`; wire it from the
Agent Loops runtime. Preserve the existing file repository only as a test/legacy
adapter until explicitly migrated or removed in a later, authorized task.

Only two logical tables are required now:

| Table | Required stored data | Why it exists now |
| --- | --- | --- |
| `loop_tasks` | task UUID, owner IDs, `agent_id`, title, lifecycle status, current run state, `next_event_sequence`, timestamps, pending-confirmation payload if any | A conversation must survive Core restart and be reopenable from Linux or Android. |
| `loop_task_events` | task UUID, `sequence`, type, payload, timestamp | The visible transcript and the model's conversation context must have deterministic ordering independent of timestamps. |

Do not implement the long-term `loop_task_inbox` or `loop_tool_approvals` tables.

### Ordering and restart rule

The SQLite repository owns allocation of a positive, strictly increasing event
sequence per task. It must serialise `next_event_sequence` update plus event
append under one repository lock. On runtime start, it must set/reconcile the
next sequence from the maximum persisted sequence before appending another
event. Event reads sort by `(task_id, sequence)`, never by timestamp or SQLite
row-return order.

`SQLiteStore` stores JSON documents and does not expose a transaction helper.
For this weekend's single-process Core, a repository `RLock` plus the restart
reconciliation rule is sufficient. Keep that logic inside the repository so the
full architecture can later replace it with a transactional implementation
without changing the runtime or API.

### Task semantics in this slice

One `AgentLoopTask` is one user-visible conversation with exactly one agent.
Add lifecycle values needed for this use: `idle`, `running`, `awaiting_approval`,
`stopped`, and `archived` (or equivalent precise enum values). A completed model
run returns the task to `idle`; it does not close the conversation. A later
user message starts a new run against the same ordered event stream.

Persist final events only. Do not persist every streamed token/chunk. A single
in-memory live-activity field may drive the running indicator, and loss of that
ephemeral activity on Core restart is acceptable.

## Minimum conversation/runtime flow

The loop processes one submitted user message at a time. The send endpoint must
reject new messages while the task is `running` or `awaiting_approval` with a
clear conflict response. Sophisticated in-flight interruption belongs to the
full blueprint.

```text
Flet client -> POST user message
Core -> append USER_MESSAGE(sequence n), mark running, start background run
Runner -> resolve agent and its effective assigned tools
Runner -> model turn using ordered conversation + tool definitions
  normal final response -> append ASSISTANT_MESSAGE, mark idle
  tool request(s) -> for each request in order:
      append TOOL_REQUESTED
      ToolManager executes it
      append TOOL_RESULT or TOOL_FAILED
      continue model turn with prior result(s)
  confirmation required -> append TOOL_AWAITING_APPROVAL, mark awaiting_approval
Approve -> execute that exact persisted ToolCall with approval_granted=True,
           append result, resume next model turn
Deny -> append denied tool result, resume next model turn
```

The executor must preserve its existing maximum-model-turn and maximum-tool-call
guards for a single submitted message. Defaults may remain `max_model_turns=10`
and `max_tool_calls=10`; make them configurable in the server-side task request,
but do not put agent-control settings in the MVP UI.

### Model conversation format

`YsparrModelExecutor._build_user_prompt()` must be extended to construct a
bounded, ordered transcript from `loop_task_events`:

```text
User: <user message>
Assistant: <assistant message>
Tool request: <name and JSON arguments>
Tool result (<name>, <status>): <JSON result or error>
```

The current task brief, selected agent system prompt, and tool instructions from
`extend_system_prompt_with_tools()` remain in place. On each continuation turn,
the model receives all events for the active message plus enough preceding
conversation events to stay coherent. If output must be capped, truncate old
events or individual tool output with an explicit marker; never silently change
or omit the persisted transcript shown to Nick.

The parser already extracts zero or more `<tool_call>{...}</tool_call>` blocks.
Execute requests sequentially in model order and only make the next model turn
after all immediately executable requested calls have produced a result. This is
what enables several model/tool continuation cycles for one user request.

Malformed tool-call text must become a visible failed tool event or a model
format-error continuation; it must never crash the background runner or be
treated as a successful tool call.

## Tool confirmations: smallest safe integration

`ToolExecutor.execute()` already returns `ToolResult(status="pending_confirmation")`
when the effective assigned tool requires confirmation and
`approval_granted=False`. It also records the tool audit event. `ToolManager`
can execute the same `AgentTool` call when invoked with
`approval_granted=True`.

Implement only this adapter state in Agent Loops:

1. When the result is `pending_confirmation`, persist the exact existing
   `ToolCall` data (`tool_id`, `arguments`, `requester_agent_id`, `call_id`) in
   the task and append `TOOL_AWAITING_APPROVAL`.
2. The shared terminal presents the tool name, description, arguments, read-only
   flag, and Approve/Deny controls on both platforms.
3. `approve` invokes `ToolManager.execute_tool_call(the_persisted_call,
   approval_granted=True)` exactly once, appends its actual result, clears the
   pending state, and resumes the model continuation.
4. `deny` appends a normal failed/denied `TOOL_RESULT` explaining that the user
   declined it, clears pending state, and resumes the continuation without
   calling the provider.

Agent Tools remains the source of the confirmation rule and the executor. Agent
Loops does not add a second assignment, override, or policy store. There is no
separate approval table in this slice; the task's single persisted pending call
is enough because only one task run is active at a time.

Tools without confirmation execute immediately. For the first OpenIPE write,
mark the normal tool definition/assignment confirmation-required if Nick wants
an approval step. Read tools such as the current `ipe.whatDoIDo` definition can
remain immediately executable when their normal assignment permits it.

## API: only the required additions

Extend `agent_loop_routes.py` and the API-internal facade. All existing session,
active-module, and owner/group authorization checks apply.

| Endpoint | Quick-start behavior |
| --- | --- |
| `GET /agent-loops/tasks?agent_id=` | Return the authenticated user's non-archived task summaries for the selected agent. |
| `POST /agent-loops/tasks` | Create an idle task for an existing `agent_id`; no tools are accepted. |
| `GET /agent-loops/tasks/{task_id}` | Return task metadata and its ordered final events. This is sufficient polling for MVP. |
| `POST /agent-loops/tasks/{task_id}/messages` | Accept one user message, append it, and start the background run. Return task state immediately. |
| `POST /agent-loops/tasks/{task_id}/stop` | Cooperatively cancel the current model/tool operation when practical, append `TASK_STOPPED`, and return the task to stopped/idle as defined by the task state machine. |
| `POST /agent-loops/tasks/{task_id}/approval` | Body `{ "decision": "approve" | "deny" }`; act only on the persisted pending call. |
| `POST /agent-loops/tasks/{task_id}/archive` | Archive an idle/stopped task. The client asks confirmation before calling it. |

Do not add event-cursor long polling, WebSocket/SSE, or multi-task concurrent-run
APIs now. The `GET task` transcript shape must expose event `sequence` now so
the later cursor endpoint can be additive.

## Shared Flet terminal and platform shells

Create `src/apmatia/interfaces/flet/common/agent_loop_terminal/` before either
platform integration. It is the single implementation of Agent Loops client
behavior, not a portable-view renderer workaround and not duplicated client
code. It contains:

- task/event DTOs and the Agent Loops methods in `ApmatiaApiClient`;
- terminal view-model state: selected agent/task, ordered event map keyed by
  sequence, running status, pending approval, and transient request errors;
- agent/task selection, task creation/archive confirmation, composer/send,
  Stop, approve/deny, polling, retry, and event deduplication;
- chronological event controls and terminal theme tokens; and
- responsive terminal composition that works at narrow and desktop widths.

Linux and Android hosts only supply startup, connection configuration, login
shell integration, and platform-appropriate outer layout. They must call the
same shared feature with the same Core API; neither owns conversation state.

Required controls only:

- existing-agent selector sourced from Core;
- task selector/list for that selected agent and **New Task**;
- confirmation dialog before archiving the current task for **New Task**;
- chronological dark terminal feed (black/dark background and bright-green
  primary text) for user, assistant, tool requested, tool result/error, and
  approval events;
- text composer and Send;
- visible task status (`idle`, `thinking`, `using tool`, `awaiting approval`,
  `stopped`);
- Stop while running when the existing cancellation mechanism is available;
- Copy control for assistant and tool-result text;
- Approve/Deny only when Core reports a pending confirmation.

Poll `GET /agent-loops/tasks/{id}` about once a second while the selected task
is running or awaiting approval. Use `page.run_task()` like the existing
`ApmatiaShell._poll_agent_loop()` implementation. The shared event reducer must
ignore any sequence already rendered, so reconnect/poll retries are safe.
Disable Send while running in this quick-start and explain why in the status
text; later it becomes the durable interruption inbox behavior from the full
blueprint.

Add task/list/message/approval/archive methods to
`src/apmatia/interfaces/flet/common/api_client.py`. Do not expose passwords,
session cookies, or secrets in the feed or Flet logs.

### Android minimum shell and test setup

Add `src/apmatia/interfaces/flet/android/__init__.py`, `main.py`, `app.py`, and
`configuration.py`. `main.py` calls `ft.run()` and `app.py` hosts the shared
authentication and Agent Loops terminal flow; it must not import Linux window
configuration or desktop-only shell controls.

Add a platform-safe shared storage helper used by both endpoint configuration
and `ApmatiaApiClient` session persistence. It uses `APMATIA_FLET_SESSION_FILE`
when explicitly set; otherwise it uses `FLET_APP_STORAGE_DATA` in a packaged
Flet Android app, and retains the current user configuration-directory fallback
for Linux. Store only the configured Core API URL and revocable session cookie,
never a password.

Android configuration needs one editable Core URL field before login and a
small connection/settings action after login. Normalize an entered host/IP to
an `/api` base URL using the existing Linux `normalize_core_url()` behavior,
then rebuild the common API client and reconnect. The Core task/transcript is
always server-side, so Linux and Android naturally see the same selected task
and events.

The repository currently pins Flet 0.86.4 in `requirements.txt`/`uv.lock` and
has no Android client, Android SDK setup, or Flet build configuration. Use a
physical Android device with Developer options and USB debugging as the
weekend target; it is faster than establishing emulator images. The minimum
environment gate is:

1. install Android Studio/SDK platform tools only as needed for `adb`, connect
   one physical device, and verify it with `adb devices`;
2. run `uv run flet doctor` and resolve only the Android/Flutter requirements it
   reports for the pinned Flet version;
3. add minimal `[tool.flet]` metadata and Android manifest configuration to
   `pyproject.toml`, including `[tool.flet.android.manifest_application]`
   `usesCleartextTraffic = "true"` for trusted LAN/VPN HTTP development;
4. build a debug/sideload APK with the installed CLI's verified equivalent of
   `uv run flet build apk --module-name apmatia.interfaces.flet.android.main`;
   use `--arch arm64-v8a` when that is the physical device ABI; and
5. install with `adb install -r <built-apk>`, set the Core LAN/VPN URL in the
   app, and run the acceptance journey against the same Core as Linux.

The cleartext manifest setting is a contained development accommodation, not a
claim that LAN HTTP is production-safe. HTTPS/reverse-proxy deployment remains
deferred. No emulator, biometrics, notifications, attachments, or Android
navigation polish is required for this quick-start.

## Phases

### Phase 1 — durable single-agent loop, proven without OpenIPE

**Implementation**

1. Add SQLite `loop_tasks` and `loop_task_events` repository support, runtime
   wiring, ordered event types, and idle/running task lifecycle.
2. Extend the current `AgentLoopExecutor`/`YsparrModelExecutor` so a submitted
   user message produces final transcript events and loops across any number of
   sequential tool/model cycles within the configured guards.
3. Continue using `ToolManagerToolExecutor`; it must resolve only the selected
   agent's current assignments.
4. Add the small task/message/get/stop API surface.
5. Create a deterministic harmless test provider (for example `test.echo`) in
   test setup only. It returns predictable structured output and is assigned to
   one test agent.

**Focused tests**

- normal assistant response with no tool call;
- one assigned deterministic tool call followed by final assistant response;
- several sequential tool/model cycles in one message;
- tool failure returned to the model and reflected in the transcript;
- malformed/invalid tool request becomes a controlled failure;
- effective assigned-tool resolution and prevention of unassigned tool use;
- sequence ordering remains correct after reload/repository restart;
- maximum model-turn/tool-call limits terminate a confused model safely;
- Stop cancels an injectable blocking model/tool and leaves a readable task.

**Exit criterion**

An API integration test creates an existing test agent, assigns the deterministic
tool, sends a message that requires two sequential calls, and verifies the
ordered persisted transcript ends in the model's final answer.

### Phase 2 — shared terminal and Linux integration

**Implementation**

1. Add common API-client methods and the minimal shared terminal controls under
   `interfaces/flet/common/agent_loop_terminal/`; write these without Linux
   imports or desktop-width assumptions.
2. Mount the terminal for the existing `agent_loops.loops.view` route in the
   Linux shell while retaining the existing module navigation/catalog.
3. Implement agent selection, create/select task, terminal polling, Send,
   status, Stop, Copy, and New Task archive confirmation.
4. Add the minimal persisted pending-confirmation task state and API/UI
   Approve/Deny flow described above.

**Focused tests**

- Flet unit tests render each event type and status;
- Send is disabled during a running task and enabled once idle;
- polling refreshes final events in sequence without duplicates;
- New Task requires confirmation and archives only the selected idle/stopped
  task;
- a confirmation-required assigned test tool shows Approve/Deny; approve runs
  the existing tool-manager execution path once, while deny does not call the
  provider;
- existing Linux login-to-Agent-Loops journey remains intact.

**Exit criterion**

With Core running locally, Nick can select an existing test agent in Linux Flet,
watch its deterministic tool call and result, and receive the final answer from
one terminal conversation. This proves the shared terminal against a real host.

### Phase 3 — Android host for the same shared terminal

**Implementation**

1. Add the thin Android package and platform-safe storage/configuration helper
   described above; do not duplicate terminal state, controls, or API calls.
2. Add editable endpoint/login flow, persisted session, and a narrow-screen
   shell that renders the common Agent Loops terminal.
3. Add the minimal Flet/Android metadata and build configuration, verify the
   pinned Flet 0.86.4 toolchain with `uv run flet doctor`, build an APK, and
   sideload it on one physical USB-debugging Android device.

**Focused tests**

- configuration/storage tests: endpoint normalization, endpoint persistence,
  Android storage-path selection, session restore, and logout cleanup;
- shared-terminal tests run identically under the Android host for agent/task
  selection, event rendering, Send, running status, Stop, and Approve/Deny;
- a device smoke test confirms login, LAN/VPN Core connection, task selection,
  deterministic tool transcript, and reconnect after app relaunch.

**Exit criterion**

An Android device connects to the same Core as Linux, opens a task created from
Linux (or creates one itself), sees the same ordered transcript, and completes
a deterministic assigned-tool conversation through the shared terminal.

### Phase 4 — executive assistant and OpenIPE acceptance from both hosts

**Implementation**

1. Verify the real executive-assistant agent exists, has a working model, and
   can use a simple existing assigned tool before changing OpenIPE tooling.
2. Outside Agent Loops implementation, give the agent/toolsmith workflow the
   OpenIPE API documentation and the normal Apmatia tool-definition/provider
   format. Create/register/assign OpenIPE read and write tools through the
   ordinary Agent Tools pathway.
3. Ensure the providers call the OpenIPE API/service layer, never its database
   directly and never Agent Loops special-case code.
4. Exercise a read-only OpenIPE request, then a confirmation-required safe
   OpenIPE write, through the shared terminal from Linux and Android.

**Focused tests**

- OpenIPE provider contract tests for its read response and safe write response;
- tool-manager assignment/confirmation tests for the executive assistant;
- end-to-end acceptance using a harmless OpenIPE test fixture or sandboxed
  provider: read -> model reasoning -> final response, then approved write ->
  actual result -> truthful assistant report;
- the same real-Core acceptance journey from Linux and the physical Android
  device, confirming both inspect the same server-side task/event state.

**Exit criterion**

From both Linux Flet and Android Flet, connected to the same Core, the executive
assistant answers “What should I work on today?” using assigned OpenIPE read
tools as needed. It can also perform the requested highest-priority task write
only after the normal assigned OpenIPE tool succeeds (and after confirmation
when that tool requires it), then reports the actual result. Android contains
no special OpenIPE execution logic.

## Explicit non-goals

- durable FIFO interruption inbox, safe-point user interruption, or special
  tool-disabled acknowledgement turns;
- multiple simultaneous task runs or multi-agent conversations;
- event cursor endpoint, long polling, WebSocket, or SSE;
- persistence of partial streaming chunks;
- transcript summarization, attachments, export, search, or collapsed output;
- biometric authentication, Android notifications, attachment support, rich
  mobile navigation, and Internet-facing HTTPS deployment;
- agent/tool assignment screens or a parallel tool-approval policy;
- special OpenIPE runtime/database integration.

# Path Back to the Full Agent Loops Blueprint

| Full-blueprint capability | Quick-start position | Later work | Replace or extend? |
| --- | --- | --- | --- |
| `loop_tasks` + ordered event store | Implements the first two tables and sequence-bearing events now. | Add durable inbox and approvals tables when concurrency/interruption requires them. | Extend, not replace. |
| Transactional sequence allocation | Uses a repository lock plus startup reconciliation around `SQLiteStore`. | Upgrade repository internals to true SQLite transaction/constraint guarantees. | Extend internal implementation, not runtime/API contract. |
| User interruption safe points | Deferred; Send is disabled while running. | Add `loop_task_inbox`, FIFO dequeue, safe-point checks, and tool-disabled acknowledgement turns in full Phase 3. | Extend the existing executor. |
| Durable approval records | Keeps one pending call on its task and delegates policy/execution to Agent Tools. | Add `loop_tool_approvals`, richer audit/recovery, and concurrent approval handling. | Extend, not replace. |
| Cursor long polling / real-time transport | Uses whole-task polling while active. Events already have sequences. | Add the `after` cursor endpoint and long polling, then SSE/WebSocket only if needed. | Extend, not replace. |
| Streaming activity persistence | Keeps final events only; live status is ephemeral. | Persist replaceable activity records if the full terminal needs recovery of streamed text. | Extend event rendering/storage. |
| Shared Linux/Android terminal | Implements common terminal controls, state, API operations, and polling now; Linux and Android host the same feature. | Add richer adaptive layout, navigation, notifications, and more transport options as needed. | Extend, not replace. |
| Multiple conversations and agents | Supports multiple archived/idle tasks per agent but one active run per task/client. | Add concurrent-client semantics and multi-agent orchestration after the single-agent contract is proven. | Extend, not replace. |
| HTTPS, biometrics, polish | Deferred deliberately. | Apply deployment/security/UI improvements in full post-MVP phases. | Extend, not replace. |

Nothing in quick-start should be discarded for the destination architecture. The
only deliberately provisional mechanism is the repository's single-process
sequence implementation; its interface and externally visible sequence contract
remain the foundation to extend.
