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


def list_ai_model_executions(model_id: int | None = None) -> list[dict]:
    return get_execution_status(model_id=model_id)["items"]


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


def get_ai_model_executor_runtime_config() -> dict:
    return asdict(get_runtime_config())


def update_ai_model_executor_runtime_config(**payload) -> dict:
    return update_runtime_config(**payload)
