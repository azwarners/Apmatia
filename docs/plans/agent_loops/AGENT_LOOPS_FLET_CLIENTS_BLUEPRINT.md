# Agent Loops Flet Clients Blueprint

## Purpose

Build Android and Linux Flet clients for the existing `agent_loops` module.
They are transparent, tool-enabled conversations with an existing agent:

- The **Agents** module remains the authority for an agent's identity, prompt,
  model, and assigned tools.
- The **Agent Tools** module remains the authority for availability,
  confirmation requirements, execution, and audit records.
- **Agent Loops** owns task conversations, their ordered transcript, execution
  state, and the orchestration needed to safely accept a user interruption.
- Each client displays user messages, assistant messages, tool requests, tool
  results, errors, and approval requests in one chronological terminal feed.

OpenIPE is not a special runtime mode. It is a useful first agent profile: an
existing executive-assistant agent that already has OpenIPE tools assigned.

## Decisions

| Concern | Decision |
| --- | --- |
| Conversation storage | Add a dedicated SQLite database for `loop_tasks`; do not reuse Discuss storage or the current JSON task files. |
| Task lifecycle | Selecting **New Task** archives the current task after confirmation, then opens an empty task for a selected agent. |
| Tool source | Resolve tools from the selected agent's existing assignments at each model turn. Agent Loops never manages assignments. |
| User interruption | Finish the one in-flight assistant generation or one in-flight tool call. Before any next tool call or continuation turn, process the oldest queued user message and create an assistant acknowledgement/reply. |
| Approval | A confirmation-required tool pauses the task. The client presents its exact arguments and **Approve** / **Deny** actions. |
| UI architecture | Build a native terminal feature shared under `interfaces/flet/common/`; Linux and Android supply only platform startup, configuration, and layout shell code. Do not force this live interaction through the generic portable-view renderer. |
| Transport | REST with cursor-based long polling for MVP. Add WebSocket/SSE only if polling proves insufficient. |
| Authentication | Password login and persisted session cookie. Android endpoint configuration is editable. HTTPS is a follow-up, not an MVP dependency. |

## System shape

```text
Android Flet ─┐
              ├─ common agent-loop terminal ─ Apmatia API ─ Agent Loops service
Linux Flet ───┘                                      │             │
                                                     │             ├─ Agents (selected agent)
                                                     │             ├─ Agent Tools (assigned tools + audit)
                                                     │             └─ loop_tasks SQLite database
                                                     │
                                                     └─ OpenIPE tools (when assigned to that agent)
```

No Flet client executes a tool locally. Core authenticates the user, resolves
the selected agent, and executes tools server-side. This preserves the API/core
boundary and makes Linux and Android views of the same task consistent.

## Persistence model

Create a `SQLiteLoopTaskBundle` backed by the persistence module's
`SQLiteStore`, following the existing module bundle pattern. The default file
should live under the Agent Loops workspace, for example
`<agent-loops-workspace>/loop_tasks.db`; an environment override supports tests.

Use these logical tables (the physical representation may use JSON columns when
appropriate for the existing `SQLiteStore`):

| Table | Essential fields | Role |
| --- | --- | --- |
| `loop_tasks` | `id`, owner IDs, `agent_id`, `title`, `status`, `created_at`, `archived_at`, `last_event_sequence` | One user-visible task/chat with one selected agent. |
| `loop_task_events` | `id`, `task_id`, monotonic `sequence`, `event_type`, `payload`, `created_at` | Immutable, ordered transcript and runtime audit trail. |
| `loop_task_inbox` | `id`, `task_id`, `client_message_id`, `text`, `state`, `received_sequence`, `processed_sequence` | Durable FIFO user messages waiting for their safe point. `client_message_id` is unique per task for retry safety. |
| `loop_tool_approvals` | `id`, `task_id`, `tool_call_id`, exact request payload, `state`, `decided_by_user_id`, timestamps | Durable approval decision for one confirmation-required tool call. |

Event types must distinguish at least: `user_message_queued`,
`user_message_processed`, `assistant_activity`, `assistant_message`,
`tool_requested`, `tool_awaiting_approval`, `tool_approved`, `tool_denied`,
`tool_completed`, `tool_failed`, `task_stopped`, and `task_archived`.

Sequence numbers are allocated atomically inside the repository. They are the
only sync cursor exposed to clients; timestamps are display data, not ordering.

## Runtime contract

The present `AgentLoopTask` one-shot executor is a useful starting point but
must become task-conversation orchestration rather than the source of
conversation history.

1. `POST message` writes the user message and `user_message_queued` event in
   one repository operation, then wakes the task runner.
2. While a model response is streaming, its visible chunks are persisted as
   replaceable `assistant_activity` updates. The final assistant text is stored
   once as an immutable `assistant_message` event.
3. A currently executing tool runs to completion. If the model emitted several
   tool requests, do **not** begin the next one when the inbox is nonempty.
4. At that safe point, dequeue exactly one message, append
   `user_message_processed`, and run a priority acknowledgement turn with tools
   disabled. The response is persisted as `assistant_message`.
5. Resume normal continuation only after that acknowledgement is complete.
   Additional queued messages repeat the same rule in FIFO order.
6. A tool marked confirmation-required creates `tool_awaiting_approval` and
   changes task status to `awaiting_approval`; it does not execute or silently
   fail. Approve resumes that exact request once; deny appends a denied result
   and lets the model continue with that result.
7. Stop is cooperative: request cancellation, stop the currently cancellable
   model/tool operation, write a terminal event, and leave the transcript
   readable. It never deletes task data.

The model prompt is assembled from a bounded transcript window plus a persisted
summary. Tool output is included verbatim in the event stream, while prompt
construction may truncate very large output with an explicit truncation marker.
This lets the human inspect raw output even when the model receives a compact
context.

## API contract

All endpoints require the active `agent_loops` module and the normal session.
Every task lookup verifies ownership/membership before returning or mutating it.

| Endpoint | Purpose |
| --- | --- |
| `GET /agent-loops/tasks` | List non-archived tasks, filterable by `agent_id`; returns latest status and preview. |
| `POST /agent-loops/tasks` | Create a task for an existing `agent_id`. No tool list is accepted. |
| `POST /agent-loops/tasks/{id}/messages` | Queue a message with `client_message_id`; returns the accepted event sequence. |
| `GET /agent-loops/tasks/{id}/events?after=<sequence>&wait_seconds=20` | Cursor-based long poll returning ordered events, current status, and the next cursor. |
| `POST /agent-loops/tasks/{id}/stop` | Request a cooperative stop. |
| `POST /agent-loops/tasks/{id}/archive` | Archive only after a client-side confirmation; reject while running unless the request also stops it. |
| `POST /agent-loops/tasks/{id}/approvals/{approval_id}` | Accept `approve` or `deny`; records the authenticated user's decision. |

The API response for a tool request/approval includes tool name, description,
arguments, whether it is read-only, and confirmation status. It must never
expose credentials or tool-provider secrets.

## Flet client design

Create a shared feature package beneath
`src/apmatia/interfaces/flet/common/agent_loop_terminal/` with:

- API operations and DTOs added to the common API client.
- Task list/agent selector, terminal event renderer, composer, polling
  controller, and copy-output helper.
- A view-model that deduplicates events by sequence and safely restores after a
  network retry.
- Theme tokens for the terminal: black/dark background, bright green primary
  text, muted green metadata, clear status/error/approval accents, and mobile
  readable contrast.

Platform packages stay thin:

- `src/apmatia/interfaces/flet/linux/`: hosts the shared terminal in the
  existing desktop shell and retains Linux configuration behaviour.
- `src/apmatia/interfaces/flet/android/`: new app entry point, Android-friendly
  responsive layout, editable Core endpoint, password login, and persisted
  session cookie.

MVP terminal controls: agent selector, task selector/history, **New Task**
with confirmation, message composer/send, stop, status indicator, copy on
assistant/tool output, and approve/deny controls when an event requires it.
Tool results are fully visible initially; collapse/expand is later polish.

## Endpoint configuration and security

Android stores the API base URL as user-editable application configuration. It
must normalize an entered host/IP to an `/api` base URL and show the active
endpoint on the connection/login screen. The default can remain the local LAN
development address supplied at build/run time.

For MVP, HTTP is permitted for a trusted LAN/VPN deployment only. The blueprint
must keep transport concerns in configuration so a later HTTPS rollout changes
the endpoint and Android network policy, not the terminal/runtime protocol.
Do not log passwords, session cookies, tool secrets, or unredacted sensitive
arguments.

## Phased implementation plan

### Phase 0 — contracts and test seams

1. Define task/event/inbox/approval models, statuses, repository protocols, and
   test doubles in `agent_loops`.
2. Specify event payload schemas and API response DTOs.
3. Add tests for ownership checks, event ordering, idempotent message submission,
   and archived-task behaviour.

**Exit:** no client code; the model and repository interfaces make unsafe states
unrepresentable.

### Phase 1 — SQLite task transcript store

1. Implement `SQLiteLoopTaskBundle` and runtime wiring using `SQLiteStore`.
2. Migrate the module from file-backed task persistence for the new conversation
path; keep legacy files readable only if current work needs preservation.
3. Implement task create/list/get/archive and append/read-events-by-cursor.
4. Add repository concurrency locking/transactions around sequence allocation.

**Exit:** a task and complete ordered transcript survive Core restart.

### Phase 2 — single-agent conversational runtime

1. Create tasks only from existing `agent_id`; resolve its effective tool set
through the current tool manager at each normal model turn.
2. Persist streamed activity, final assistant messages, tool requests/results,
   and failures as events.
3. Build bounded transcript + summary prompt construction.
4. Implement cooperative stop and task status reporting.

**Exit:** an existing agent can converse and use its already-assigned tools with
the full exchange visible through the API.

### Phase 3 — interruption and approval state machine

1. Implement durable FIFO inbox and idempotent message acceptance.
2. Insert safe-point checks after a model completion and every tool completion.
3. Implement tool-free priority acknowledgement turns, then normal resumption.
4. Turn confirmation-required tool results into durable approval records and
   pause/resume/deny transitions.
5. Add deterministic tests for: message during streaming, message during a
   tool, multiple emitted tools, multiple queued messages, approve, deny, stop,
   and Core restart while waiting for approval.

**Exit:** the promised interruption rule is proven in tests.

### Phase 4 — API and shared terminal feature

1. Add task, message, event-cursor, stop, archive, and approval routes.
2. Add common Flet API client methods and cursor-based long-poll controller.
3. Build the shared black/green terminal view and its MVP controls.
4. Add client tests for event ordering/deduplication, send retries, terminal
   rendering, New Task confirmation, and approval actions.

**Exit:** the terminal can run in a Flet test harness against a mocked API.

### Phase 5 — Linux integration

1. Mount the shared terminal from the existing Linux shell when the Agent Loops
   view is selected.
2. Preserve the generic module catalog for navigation; only this live terminal
   receives its dedicated renderer.
3. Test login, selected-agent task creation, long polling, stop, copy, archive,
   and approval UX on desktop.

**Exit:** Linux is the first complete production-like client.

### Phase 6 — Android client

1. Add the Android Flet package and entry point under
   `src/apmatia/interfaces/flet/android/`.
2. Implement login/connection settings with editable Core URL and persisted
   session; test URL normalization and reconnect behaviour.
3. Host the shared terminal in a narrow-screen layout with touch-size controls.
4. Package and test on a physical Android device against the configured Core
   endpoint.

**Exit:** Android has functional parity with the Linux MVP for one selected
agent and one active task at a time.

### Phase 7 — post-MVP hardening

1. HTTPS/reverse-proxy deployment and Android transport policy.
2. Event streaming upgrade (SSE/WebSocket) only if long-poll latency or server
   load warrants it.
3. Biometric session gate, rich tool-result collapse/search, attachments, task
   export, resumable summaries, and multi-agent tasks.

## Explicit non-goals for MVP

- Changing the Agents module's model/prompt/tool-assignment UI.
- Local Android tool execution or direct client-to-OpenIPE access.
- Multi-agent orchestration.
- Replacing Discuss or adding tool use to Discuss.
- WebSocket/SSE, biometrics, or mandatory HTTPS before the basic flow works.

## Verification gate for every implementation phase

Run the full suite with `./test.sh`. For code changes, redeploy Core and the
Streamlit application using the repository's required deployment flow, and
exercise the relevant Flet client journey against Core.
