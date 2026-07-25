from __future__ import annotations

from dataclasses import asdict

from apmatia.modules.ai_model_executor import (
    can_run_model,
    get_execution_status,
    get_runtime_config,
    inspect_host_resources,
    list_execution_records,
    start_model,
    stop_model,
    update_runtime_config,
)
from apmatia.modules.ai_model_executor.models import TextGenerationWorkPayload


def list_ai_model_executions(model_id: int | None = None) -> list[dict]:
    return get_execution_status(model_id=model_id)["items"]


def get_ai_work_queue_status() -> dict:
    from apmatia.modules.ai_model_executor.queue import WorkQueue
    # In a real system, this would use a singleton repository
    queue = WorkQueue(work_repository=None)
    items = queue.repo.list_all() if hasattr(queue, 'repo') else []
    return {
        "items": [asdict(item) for item in items],
        "count": len(items)
    }


def enqueue_ai_work(payload: dict, priority: int = 0, runtime_id: str | None = None) -> dict:
    from apmatia.modules.ai_model_executor.queue import WorkQueue
    from apmatia.modules.ai_model_executor.models import WorkItem, TextGenerationWorkPayload
    from apmatia.core.models import utc_now

    queue = WorkQueue(work_repository=None)
    work_item = WorkItem(
        id=str(utc_now().timestamp()),
        payload=TextGenerationWorkPayload(**payload),
        priority=priority,
        runtime_id=runtime_id
    )
    queue.enqueue(work_item)
    return asdict(work_item)


def get_ai_model_executor_resources() -> dict:
    return asdict(inspect_host_resources())


def can_ai_model_run(model_id: int) -> dict:
    return can_run_model(model_id)


def start_ai_model_execution(model_id: int, **payload) -> dict:
    return start_model(model_id, **payload)


def stop_ai_model_execution(model_id: int | None = None, **payload) -> dict:
    return stop_model(model_id, **payload)


def get_ai_model_execution_status(model_id: int | None = None) -> dict:
    return get_execution_status(model_id=model_id)


def dispatch_ai_work() -> dict:
    import asyncio

    from apmatia.modules.ai_model_executor.capacity import CapacityManager
    from apmatia.modules.ai_model_executor.dispatcher import Dispatcher
    from apmatia.modules.ai_model_executor.executor import ExecutorService
    from apmatia.modules.ai_model_executor.queue import WorkQueue
    from apmatia.modules.ai_model_executor.reservation import ReservationManager

    # Simplified wiring for first slice
    runtime_repo = None
    queue = WorkQueue(work_repository=runtime_repo)
    capacity = CapacityManager(runtime_repo)
    executor = ExecutorService(runtime_repo)
    reservation = ReservationManager(runtime_repo)
    dispatcher = Dispatcher(queue, capacity, executor, reservation)

    result = asyncio.run(dispatcher.dispatch_once())
    return asdict(result) if result else {}


def get_ai_model_executor_runtime_config() -> dict:
    return asdict(get_runtime_config())


def update_ai_model_executor_runtime_config(**payload) -> dict:
    return update_runtime_config(**payload)
