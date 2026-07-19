# Revised AI Infrastructure Plan: Seats & Dispatching (v2)

## 1. Discovered Architecture
- **Canonical Execution Path**:
  `Internal API (ai_model_executor.py)` $\rightarrow$ `Module Service (ai_model_executor/services.py)` $\rightarrow$ `Library Executor (ysparr/modalities/text2text/executor.py)` $\rightarrow$ `Backend (OpenAI/KoboldCpp)`.
- **Persistence Pattern**:
  Uses a `Repository` protocol. Current implementation relies on `get_config_value` (JSON/SQLite) but moves toward a formal `Repository` $\rightarrow$ `Service` $\rightarrow$ `Model` pattern.
- **Dependency Direction**:
  `Interface` $\rightarrow$ `Internal API` $\rightarrow$ `Core/Module` $\rightarrow$ `Library` $\rightarrow$ `External Service`.

## 2. Proposed Domain Models & Placement
- **`ModelRuntime`** (in `ai_model_executor/models.py`):
  - `id`, `model_config_id`, `max_concurrency` (int).
  - *Note: `current_leases_count` is derived from active `SeatLease` records.*
- **`SeatLease`** (in `ai_model_executor/models.py`):
  - `id`, `runtime_id`, `owner_id` (WorkItem ID), `acquired_at`, `released_at`.
  - **Status (Enum)**: `active`, `released`, `failed`, `cancelled`, `expired`.
- **`WorkItem`** (in `ai_model_executor/models.py`):
  - `id`, `payload` (`TextGenerationWorkPayload`), `priority`, `runtime_id` (preferred).
  - **Status (Enum)**: `queued`, `claimed`, `running`, `completed`, `failed`, `cancelled`.

## 3. Proposed Services (The Logic)
- **`CapacityManager`** (in `ai_model_executor/capacity.py`):
  - Logic: `acquire_seat(runtime_id)` and `release_seat(lease_id)`.
  - **Consistency**: `asyncio.Semaphore` (in-memory) $\leftrightarrow$ `SeatLease` (persisted).
  - **Flow**: `acquire semaphore` $\rightarrow$ `persist active lease` $\rightarrow$ `if fail, release semaphore`.
- **`WorkQueue`** (in `ai_model_executor/queue.py`):
  - Logic: `enqueue(work_item)`, `claim_next_eligible()`.
  - **Claiming**: Atomic transition `queued` $\rightarrow$ `claimed` to avoid race conditions.
- **`Dispatcher`** (in `ai_model_executor/dispatcher.py`):
  - Logic: The loop that matches `WorkQueue` $\rightarrow$ `CapacityManager` $\rightarrow$ `Ysparr Executor`.

## 4. The First Vertical Slice
1. **Register**: Create a `ModelRuntime` with `max_concurrency=3`.
2. **Enqueue**: Submit a `WorkItem` with validated `TextGenerationWorkPayload`.
3. **Dispatch**: `Dispatcher` finds the work, checks the runtime, and calls `acquire_seat()`.
4. **Execute**: Call `ysparr` executor $\rightarrow$ get result.
5. **Release**: Call `release_seat()` $\rightarrow$ `WorkItem` marked `completed`.

## 5. Concurrency & Lifecycle
- **Consistency**: `max_concurrency` is the ceiling.
- **WorkItem Transitions**: `queued` $\rightarrow$ `claimed` $\rightarrow$ `running` $\rightarrow$ `completed`.
- **Lease Transitions**: `active` $\rightarrow$ `released` (or `failed`/`cancelled`/`expired`).
- **Failure Modes**:
  - No compatible runtime: `WorkItem` remains `queued` with diagnostic reason.
  - Compatible runtime busy: `WorkItem` remains `queued`.
  - Executor exception: `WorkItem` $\rightarrow$ `failed` or `retryable`, `SeatLease` $\rightarrow$ `released`.
  - Process restart: Persisted active leases are detected and either resumed or marked `expired`.

## 6. Deterministic Test Strategy
- **The "4-Job Test"**:
  - Runtime `max_concurrency = 3`.
  - Submit 4 `WorkItems` using `asyncio.Event` for synchronization.
  - **Proof**:
    - Exactly 3 jobs enter the executor; the 4th waits.
    - After one release, the 4th enters.
    - Max active count is exactly 3.
    - All permits and leases are released afterward.

## 7. File Changes
- **Modify**: `src/apmatia/modules/ai_model_executor/models.py` (Add Runtime, Lease, WorkItem, Payload).
- **Add/Modify**: `src/apmatia/modules/ai_model_executor/capacity.py`, `queue.py`, `dispatcher.py`.
- **Modify**: `src/apmatia/api/internal/ai_model_executor.py` (Add `enqueue_work`, `dispatch_next`).
- **Add**: `tests/modules/ai_model_executor/test_concurrency.py` (Deterministic tests).
