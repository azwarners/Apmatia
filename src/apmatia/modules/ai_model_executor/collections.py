from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apmatia.core.module_view_schema import build_collection_view_schema


# Minimal dataclass types for schema inference (these mirror executor models)
@dataclass(slots=True)
class _QueueItemSchemaType:
    """Minimal dataclass for queue item schema inference."""
    id: int = 0
    model_id: int = 0
    prompt: str = ""
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    priority: int = 0
    runtime_id: str = ""
    status: str = "queued"
    created_at: str = ""
    claimed_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    reservation_id: str | None = None


@dataclass(slots=True)
class _ReservationSchemaType:
    """Minimal dataclass for reservation schema inference."""
    id: str = ""
    runtime_id: str = ""
    owner_user_id: int = 0
    owner_session_id: str = ""
    requested_seats: int = 1
    mode: str = "shared"
    state: str = "requested"
    created_at: str = ""
    activated_at: str | None = None
    released_at: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutorCollectionViewSpec:
    action_id: str
    view_id: str
    object_type: str
    singular_label: str
    plural_label: str
    description: str
    schema: dict[str, Any]
    list_command_id: str
    create_command_id: str
    edit_command_id: str
    delete_command_id: str
    show_command_id: str = ""
    scan_command_id: str = ""


EXECUTION_VIEW_SPEC = ExecutorCollectionViewSpec(
    action_id="ai_model_executor.executions",
    view_id="ai_model_executor.executions.view",
    object_type="execution",
    singular_label="Execution",
    plural_label="Executions",
    description="Inspect and control local model execution processes (start, stop, status).",
    schema=build_collection_view_schema(
        _QueueItemSchemaType,
        list_fields=(
            "id",
            "model_id",
            "runtime_id",
            "status",
        ),
        create_fields=(
            "model_id",
            "prompt",
            "priority",
            "runtime_id",
        ),
        edit_fields=(
            "model_id",
            "prompt",
            "priority",
            "runtime_id",
            "status",
        ),
        field_overrides={
            "id": {"hidden": True},
            "prompt": {"field_type": "textarea"},
            "system_prompt": {"field_type": "textarea"},
            "reservation_id": {"hidden": True},
            "endpoint_url": {"label": "Endpoint URL"},
            "log_path": {"label": "Log Path"},
            "status": {
                "label": "Status",
                "field_type": "select",
                "options": ["running", "stopped", "error"],
            },
        },
        create={
            "title": "Start Model Execution",
            "description": "Start a local llama.cpp execution for a model.",
            "submit_label": "Start",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_executor.executions.list",
    create_command_id="ai_model_executor.executions.start",
    edit_command_id="ai_model_executor.executions.edit",
    delete_command_id="ai_model_executor.executions.stop",
    show_command_id="ai_model_executor.executions.show",
)

QUEUE_VIEW_SPEC = ExecutorCollectionViewSpec(
    action_id="ai_model_executor.queue",
    view_id="ai_model_executor.queue.view",
    object_type="queue_item",
    singular_label="Queue Item",
    plural_label="Queue Items",
    description="Inspect the work queue and dispatch items to available runtimes.",
    schema=build_collection_view_schema(
        _QueueItemSchemaType,
        list_fields=(
            "id",
            "model_id",
            "priority",
            "runtime_id",
            "status",
            "created_at",
        ),
        create_fields=(
            "model_id",
            "prompt",
            "priority",
            "runtime_id",
        ),
        edit_fields=(
            "model_id",
            "prompt",
            "priority",
            "runtime_id",
            "status",
        ),
        field_overrides={
            "id": {"hidden": True},
            "payload": {"hidden": True},
            "priority": {
                "label": "Priority",
                "help_text": "Lower number = higher priority (0=User, 1=Agent, 2=Background)",
            },
            "status": {
                "label": "Status",
                "field_type": "select",
                "options": ["queued", "claimed", "running", "completed", "failed", "cancelled"],
            },
            "created_at": {"label": "Created"},
            "claimed_at": {"label": "Claimed"},
            "completed_at": {"label": "Completed"},
            "error": {"label": "Error", "field_type": "textarea"},
            "reservation_id": {"hidden": True},
        },
        create={
            "title": "Enqueue Work",
            "description": "Add a text generation task to the queue.",
            "submit_label": "Enqueue",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_executor.queue.list",
    create_command_id="ai_model_executor.queue.enqueue",
    edit_command_id="ai_model_executor.queue.edit",
    delete_command_id="ai_model_executor.queue.cancel",
)

RESERVATION_VIEW_SPEC = ExecutorCollectionViewSpec(
    action_id="ai_model_executor.reservations",
    view_id="ai_model_executor.reservations.view",
    object_type="reservation",
    singular_label="Reservation",
    plural_label="Reservations",
    description="Manage seat reservations for model runtimes to protect interactive users from background work.",
    schema=build_collection_view_schema(
        _ReservationSchemaType,
        list_fields=(
            "id",
            "runtime_id",
            "owner_user_id",
            "requested_seats",
            "mode",
            "state",
            "created_at",
        ),
        create_fields=(
            "runtime_id",
            "requested_seats",
            "mode",
        ),
        edit_fields=(
            "requested_seats",
            "mode",
        ),
        field_overrides={
            "id": {"hidden": True},
            "owner_session_id": {"hidden": True},
            "activated_at": {"hidden": True},
            "released_at": {"hidden": True},
            "requested_seats": {
                "label": "Requested Seats",
                "help_text": "Number of concurrency seats to reserve.",
            },
            "mode": {
                "label": "Mode",
                "field_type": "select",
                "options": ["shared", "interactive_reserved", "interactive_exclusive"],
                "help_text": "shared=background can use free seats; interactive_reserved=blocks all background; interactive_exclusive=all seats reserved.",
            },
            "state": {
                "label": "State",
                "field_type": "select",
                "options": ["requested", "acquiring", "active", "releasing", "released", "cancelled", "expired", "failed"],
            },
            "created_at": {"label": "Created"},
        },
        create={
            "title": "Reserve Seats",
            "description": "Reserve seats on a model runtime for interactive use.",
            "submit_label": "Reserve",
            "cancel_label": "Cancel",
        },
    ),
    list_command_id="ai_model_executor.reservations.list",
    create_command_id="ai_model_executor.reservations.create",
    edit_command_id="ai_model_executor.reservations.edit",
    delete_command_id="ai_model_executor.reservations.release",
)

CAPACITY_VIEW_SPEC = ExecutorCollectionViewSpec(
    action_id="ai_model_executor.capacity",
    view_id="ai_model_executor.capacity.view",
    object_type="capacity",
    singular_label="Capacity",
    plural_label="Capacity",
    description="View runtime capacity, active leases, and admission control state.",
    schema={
        "version": 1,
        "fields": [
            {
                "key": "runtime_id",
                "label": "Runtime ID",
                "data_type": "string",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "total_capacity",
                "label": "Total Capacity",
                "data_type": "number",
                "field_type": "number",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "active_leases",
                "label": "Active Leases",
                "data_type": "number",
                "field_type": "number",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "reserved_capacity",
                "label": "Reserved Capacity",
                "data_type": "number",
                "field_type": "number",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "general_available",
                "label": "General Available",
                "data_type": "number",
                "field_type": "number",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "admission_mode",
                "label": "Admission Mode",
                "data_type": "string",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
        ],
        "create": {
            "title": "Capacity Status",
            "description": "View current runtime capacity and admission control state.",
            "submit_label": "Refresh",
            "cancel_label": "Cancel",
        },
    },
    list_command_id="ai_model_executor.capacity.list",
    create_command_id="",
    edit_command_id="",
    delete_command_id="",
)

RESOURCES_VIEW_SPEC = ExecutorCollectionViewSpec(
    action_id="ai_model_executor.resources",
    view_id="ai_model_executor.resources.view",
    object_type="resources",
    singular_label="Resource Snapshot",
    plural_label="Resource Snapshots",
    description="Inspect local host RAM, VRAM, and GPU resources for model execution planning.",
    schema={
        "version": 1,
        "fields": [
            {
                "key": "ram_total_bytes",
                "label": "Total RAM",
                "data_type": "number",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "ram_available_bytes",
                "label": "Available RAM",
                "data_type": "number",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "vram_total_bytes",
                "label": "Total VRAM",
                "data_type": "number",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "vram_available_bytes",
                "label": "Available VRAM",
                "data_type": "number",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "gpu_count",
                "label": "GPU Count",
                "data_type": "number",
                "field_type": "number",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
            {
                "key": "source",
                "label": "Source",
                "data_type": "string",
                "field_type": "text",
                "create": False,
                "edit": False,
                "list": True,
                "required": False,
            },
        ],
        "create": {
            "title": "Host Resources",
            "description": "Inspect local system resources.",
            "submit_label": "Inspect",
            "cancel_label": "Cancel",
        },
    },
    list_command_id="ai_model_executor.resources.inspect",
    create_command_id="",
    edit_command_id="",
    delete_command_id="",
)

AI_MODEL_EXECUTOR_COLLECTION_VIEW_SPECS: tuple[ExecutorCollectionViewSpec, ...] = (
    EXECUTION_VIEW_SPEC,
    QUEUE_VIEW_SPEC,
    RESERVATION_VIEW_SPEC,
    CAPACITY_VIEW_SPEC,
    RESOURCES_VIEW_SPEC,
)
