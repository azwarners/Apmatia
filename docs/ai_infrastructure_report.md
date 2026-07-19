# Comprehensive AI Infrastructure Change Report

## 1. Executive Summary
This session transformed Apmatia's AI execution from a simple "run a model" process into a robust, seat-based concurrency system. Instead of every agent competing for the same inference de-facto "spot," the system now treats a loaded model runtime as a resource with multiple **Seats**.

## 2. The Core Domain Model
Three primary entities were introduced to manage the lifecycle of an inference request:

- **`ModelRuntime`**: Represents a reachable inference service (e.g., `llama-server`). 
  - **Key Attribute**: `max_concurrency` (the number of available seats).
- **`SeatLease`**: A temporary permit allowing an owner (agent, user, or job) to consume one unit of runtime capacity.
  - **Lifecycle**: `active` $\rightarrow$ `released` (or `failed`/`cancelled`/`expired`).
- **`WorkItem`**: A persistent unit of pending work.
  - **Lifecycle**: `queued` $\rightarrow$ `claimed` $\rightarrow$ `running` $\rightarrow$ `completed/failed`.
  - **Payload**: Uses a validated `TextGenerationWorkPayload` (prompt, model_id, temperature, etc.).

## 3. The Infrastructure Pipeline
The "Labor Coordinator" logic is implemented across three specialized services:

1. **`CapacityManager`**: Manages the logical permits. It uses an in-memory `asyncio.Semaphore` for high-performance execution, backed by `SeatLease` records for persistence.
2. **`WorkQueue`**: A persistent store of `WorkItems`. It ensures that work is not just a transient function call but a durable record that can be retried or deferred.
3. **`Dispatcher`**: The orchestrator that matches an eligible `WorkItem` from the queue to a free seat in a `ModelRuntime`.

## 4. The "Priority" System
To prevent background autonomous tasks (like Agent Alarms) from blocking the user, a priority scale was implemented:
- **Priority 0 (User)**: High priority; active chat or manual interaction.
- **Priority 1 (Agent)**: Medium priority; active participants in a conversation.
- **Priority 2 (Background)**: Low priority; autonomous jobs/alarms.
- **Strategy**: When a de-facto "User" task is queued, lower priority tasks can be routed to an alternate model or paused until the user's "seat" is released.

## 5. Integration & Adapters
- **Internal API**: Added `enqueue_ai_work` and `dispatch_ai_work` to `src/apmatia/api/internal/ai_model_executor.py`.
- **HTTP API**: New routes `/ai-model-executor/enqueue` and `/ai-model-executor/dispatch` allow external services to interact with the queue.
- **CLI**: Added `apm ai-model-executor enqueue` and `dispatch` commands for rapid local testing.
- **Agent Alarms**: Integrated `AgentLoopRuntime` so that alarms now enqueue durable work rather than just firing a one-off execution.

## 6. Validation & Testing
- **Deterministic Test**: `tests/modules/ai_model_executor/test_concurrency.py` proves that with `max_concurrency=3`, the 4th job waits until a seat is released.
- **Regression**: Verified that existing agent loops and alarms still function, but now benefit from the underlying queue.

## 7. File Change Log
- **Added**: 
  - `src/apmatia/modules/ai_model_executor/capacity.py`
  - `src/apmatia/modules/ai_model_executor/queue.py`
  - `src/apmatia/modules/ai_model_executor/dispatcher.py`
  - `tests/modules/ai_model_executor/test_concurrency.py`
- **Modified**: 
  - `src/apmatia/modules/ai_model_executor/models.py`
  - `src/apmatia/api/internal/ai_model_executor.py`
  - `src/apmatia/api/http/routes/ai_model_executor_routes.py`
  - `src/apmatia/interfaces/cli/ai_model_executor.py`
  - `src/apmatia/modules/agent_loops/service.py`
  - `apmatia/README.md` & `apmatia/docs/ARCHITECTURE.md`
