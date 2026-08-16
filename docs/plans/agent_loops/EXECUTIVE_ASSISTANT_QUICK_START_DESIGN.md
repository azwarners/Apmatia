# Executive Assistant Quick Start — Design

## Status and authority

This is the design companion to
`EXECUTIVE_ASSISTANT_QUICK_START_BLUEPRINT.md`. That overview and
`AGENT_LOOPS_FLET_CLIENTS_BLUEPRINT.md` remain authoritative. This document
turns their quick-start decisions into a stable implementation contract; it does
not introduce a second Agent Loops architecture.

## Product boundary

The quick-start product is a server-side, single-agent task conversation:

```text
existing agent + that agent's current assigned tools + Agent Loops runtime
                       │
Linux Flet ────────────┼────────── Apmatia Core ────── Agent Tools / OpenIPE
Android Flet ──────────┘
```

OpenIPE is an ordinary capability of an existing agent. It is not a mode,
database adapter, credential store, or special case inside Agent Loops.

## Authority rules

| Concern | Owner | Agent Loops responsibility | Prohibited shortcut |
| --- | --- | --- | --- |
| Identity, system prompt, selected model, assigned tools | `modules.agents` | Load the selected `agent_id`. | Copying agent settings into a task. |
| Effective availability, input validation, confirmation policy, provider execution, audit | `ToolManager` and `ToolExecutor` | Ask for tools and execute `ToolCall`s only through the manager. | Passing a client tool list, direct provider calls, or direct OpenIPE data access. |
| Task, transcript, orchestration, run state | `modules.agent_loops` | Persist ordered events and drive continuation turns. | Creating a second chat/tool loop outside `AgentLoopExecutor`. |
| Rendering and input | Flet clients | Call Core and show its ordered state. | Local tool execution or client-local transcript truth. |

## Task conversation model

Extend `AgentLoopTask`; do not create a parallel conversation entity. One task:

- belongs to one authenticated owner/group context;
- selects exactly one existing `agent_id`;
- persists on Core and can be opened from Linux or Android;
- stays available after one agent run ends; and
- has at most one active run in the quick-start.

Task lifecycle:

```text
idle -> running -> idle
              ├-> awaiting_approval -> running -> idle
              ├-> stopped
              └-> failed
idle/stopped -> archived
```

`archived` tasks are retained but excluded from normal task selection. A client
must confirm before archiving the selected idle/stopped task to create a new
one. A task does not become permanently completed merely because one submitted
user message received a final answer.

## Persistence contract

The quick-start subset is a new `loop_tasks.db` at the Agent Loops workspace
root. Its repository implementation uses `SQLiteStore` behind
`SQLiteLoopTaskBundle` in `src/apmatia/modules/agent_loops/sqlite_repositories.py`.

| Logical table | Required fields |
| --- | --- |
| `loop_tasks` | UUID, owner IDs, `agent_id`, title, status, run counters/state, `next_event_sequence`, timestamps, optional one pending `ToolCall` payload. |
| `loop_task_events` | task UUID, positive sequence, type, JSON payload, timestamp. |

The event repository, not callers, allocates sequence numbers. Within its
single-process lock, it increments `next_event_sequence` and appends the event.
It reconciles the next value from persisted events when the runtime starts.
All transcript reads sort by sequence. Timestamps are display information only.

Persist final messages and tool state, but not every streaming chunk. Current
model activity may exist in memory solely to render `thinking` / `using tool`.

### Required event payloads

Use the existing `LoopEvent` with extended `LoopEventType` values. Each payload
must be JSON serializable and sufficient to render the transcript without a
second request:

| Event | Payload minimum |
| --- | --- |
| `USER_MESSAGE` | `message_id`, `text` |
| `ASSISTANT_MESSAGE` | `text`, `run_turn_index`, optional model usage |
| `TOOL_REQUESTED` | tool name, selected tool ID, call ID, arguments, turn/index |
| `TOOL_RESULT` / `TOOL_FAILED` | tool name, call ID, status, result/error, metadata |
| `TOOL_AWAITING_APPROVAL` | tool name, description, arguments, call ID, read-only flag |
| `TASK_STOPPED` / `TASK_FAILED` | reason/error |
| `TASK_ARCHIVED` | archive timestamp/reason if supplied |

Existing generic lifecycle events may remain for logging compatibility, but the
terminal reads the explicit conversation events above.

## Agentic run contract

For one accepted user message:

1. Core appends `USER_MESSAGE`, marks task `running`, and starts the existing
   background `AgentLoopRuntime` runner.
2. `ToolManagerToolExecutor.list_tools()` resolves the selected agent's
   effective assigned tools immediately before each normal model turn.
3. `YsparrModelExecutor` builds the selected agent's system prompt and a bounded
   ordered transcript. Tool definitions are supplied with
   `extend_system_prompt_with_tools()`.
4. `AgentLoopExecutor` calls the model. A normal response becomes an
   `ASSISTANT_MESSAGE` and returns the task to `idle`.
5. Each parsed `<tool_call>` executes in model order. Persist `TOOL_REQUESTED`,
   call `ToolManager.execute_tool_call`, persist actual result/failure, then
   supply the result to the next model turn.
6. Continue until a model turn has no tool request, Stop succeeds, a failure is
   terminal, or the configured model/tool guard is reached.

The executor must support more than one model/tool continuation cycle. It must
not assume one model call or one tool call ends a user request.

### Model transcript format

`YsparrModelExecutor._build_user_prompt()` creates clear role-labelled input in
sequence order:

```text
User: <text>
Assistant: <text>
Tool request (<name>): <arguments JSON>
Tool result (<name>, <status>): <result JSON or error>
```

The task brief and existing agent system prompt remain separate from transcript
content. Cap prompt size with explicit truncation markers, never by changing the
stored events. Invalid JSON/schema/tool-name failures must appear as failures in
the transcript and reach a continuation turn when safe.

### Guards and Stop

Retain `max_model_turns` and `max_tool_calls`; default each to 10 for this
slice. A limit produces a terminal visible event and a task state from which the
user can read the transcript or start a new task. The existing cancellation
token/backend stop hooks remain the Stop mechanism. A stopped run does not erase
the task or transcript.

### Deliberate quick-start limit

Core rejects a new message while the task is `running` or `awaiting_approval`.
There is no user-interrupt inbox, safe-point interruption, or acknowledgement
turn yet. This is a runtime-complexity deferral, not a client limitation.

## Confirmation-required tool contract

Agent Tools already makes this decision. When `ToolManager.execute_tool_call()`
returns `pending_confirmation`:

1. Agent Loops stores that exact `ToolCall` as the task's sole pending call,
   appends `TOOL_AWAITING_APPROVAL`, and marks the task `awaiting_approval`.
2. Either client renders its arguments and sends `approve` or `deny` to Core.
3. Approve calls the same persisted `ToolCall` once with
   `approval_granted=True`; Agent Tools still performs validation, provider
   execution, and audit.
4. Deny appends a denied tool result without invoking the provider.
5. Both decisions clear the pending call and resume the model continuation with
   the resulting tool outcome.

There is no new assignment mechanism, approval policy, or quick-start approval
table. The full blueprint adds durable multi-approval machinery later.

## Core API contract

All routes remain in `src/apmatia/api/http/routes/agent_loop_routes.py`, require
the active module/session, and verify access before reading/mutating tasks.

| Route | Contract |
| --- | --- |
| `GET /agent-loops/tasks?agent_id=` | List non-archived task summaries for one existing selected agent. |
| `POST /agent-loops/tasks` | Create idle task from `agent_id` and optional title. Reject tool input. |
| `GET /agent-loops/tasks/{id}` | Return task state plus all ordered final events for MVP polling. |
| `POST /agent-loops/tasks/{id}/messages` | Accept a nonblank message only while idle/stopped; append event and start run. |
| `POST /agent-loops/tasks/{id}/stop` | Request cooperative cancellation and return current task. |
| `POST /agent-loops/tasks/{id}/approval` | Accept only `approve`/`deny` for the one pending call. |
| `POST /agent-loops/tasks/{id}/archive` | Archive idle/stopped task only. |

No cursor event route, streaming transport, client-supplied tool list, or
concurrent-run API is part of this slice. Event sequences are present now so the
full cursor contract is additive.

## Shared client contract

`src/apmatia/interfaces/flet/common/agent_loop_terminal/` is the shared feature
package. It owns:

- API DTO conversion and task/message/approval operations;
- terminal view model and event reducer keyed by event sequence;
- agent/task selection, task creation/archive confirmation, composer/send,
  polling, retry/deduplication, Stop, Copy, and approval controls;
- chronological event controls and black/dark, bright-green terminal tokens;
- narrow/desktop responsive composition.

The Linux host integrates this feature into the current authenticated
`ApmatiaShell`. The Android host supplies only an app entry, connection/login
shell, platform-safe storage/configuration, and responsive outer layout. Both
use the same Core task IDs and event sequences; no task is stored on either
device.

### Android contract

`src/apmatia/interfaces/flet/android/` contains `__init__.py`, `main.py`,
`app.py`, and `configuration.py`. It does not import desktop window code.

A shared storage helper stores only endpoint configuration and the revocable
session cookie. It honors `APMATIA_FLET_SESSION_FILE`, then uses
`FLET_APP_STORAGE_DATA` when packaged, and retains the Linux configuration path
fallback. Android has an editable Core endpoint before login and a small
connection setting after login; it normalizes host/IP input to `/api` using the
existing Linux URL normalization rule.

The physical-device target is the quickest reliable verification path. Flet is
pinned at 0.86.4; use `uv run flet doctor`, build a sideload APK, and test via
USB debugging. Trusted LAN/VPN HTTP development uses the minimal Flet manifest
application setting `usesCleartextTraffic = "true"`; HTTPS is intentionally
deferred.

## Explicit non-goals

- user interruption inboxes and special acknowledgement turns;
- multi-agent tasks and multiple simultaneous task runs;
- partial-token persistence, cursor polling, WebSocket, or SSE;
- Android biometrics, notifications, attachments, elaborate navigation, and
  transcript-search polish;
- Internet-facing production deployment/mandatory HTTPS; and
- any special OpenIPE execution or storage path.

## Evolution rule

All quick-start code is a foundation for the full Agent Loops blueprint:

- add inbox/approval tables and transactional persistence later;
- add cursor/streaming transport without changing client event semantics;
- add richer shared-client layout and Android polish without duplicating the
  terminal; and
- extend the executor rather than replacing the general agent/tool loop.
