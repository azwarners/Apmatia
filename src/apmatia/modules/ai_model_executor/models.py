from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apmatia.lib.apmatia_core.models import ApmatiaObject, utc_now


@dataclass(slots=True)
class LlamaCppRuntimeConfig:
    runtime_id: str = "llama_cpp"
    executable_path: str = "llama-server"
    default_args: tuple[str, ...] = ()
    host: str = "127.0.0.1"
    default_port: int = 8000
    stop_conflicting_models: bool = True
    log_dir: str = ""


@dataclass(slots=True)
class ModelRuntime(ApmatiaObject):
    id: str | None = None
    model_config_id: int | None = None
    max_concurrency: int = 1
    endpoint_url: str = ""
    capabilities: set[str] = field(default_factory=set)


@dataclass(slots=True)
class RuntimeReservation(ApmatiaObject):
    id: str | None = None
    runtime_id: str | None = None
    owner_user_id: int | None = None
    owner_session_id: str | None = None
    requested_seats: int = 1
    mode: str = "shared"  # shared, interactive_reserved, interactive_exclusive
    state: str = "requested"  # requested, acquiring, active, releasing, released, cancelled, expired, failed
    created_at: datetime = field(default_factory=utc_now)
    activated_at: datetime | None = None
    released_at: datetime | None = None


@dataclass(slots=True)
class HostResourceSnapshot:
    ram_total_bytes: int = 0
    ram_available_bytes: int = 0
    vram_total_bytes: int = 0
    vram_available_bytes: int = 0
    gpu_count: int = 0
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModelExecutionRecord(ApmatiaObject):
    model_id: int = 0
    host_id: str = "local"
    runtime_id: str = "llama_cpp"
    pid: int | None = None
    port: int | None = None
    endpoint_url: str = ""
    status: str = "stopped"
    launch_command: str = ""
    log_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SeatLease(ApmatiaObject):
    """A temporary permit allowing an owner to consume one unit of runtime capacity."""
    id: str | None = None
    runtime_id: str | None = None
    owner_id: str | None = None
    acquired_at: datetime = field(default_factory=utc_now)
    released_at: datetime | None = None
    status: str = "active"  # active, released, failed, cancelled, expired
    reservation_id: str | None = None


@dataclass(slots=True)
class TextGenerationWorkPayload:
    prompt: str
    model_id: int
    system_prompt: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass(slots=True)
class WorkItem(ApmatiaObject):
    """A persistent unit of pending work in the queue."""
    id: str | None = None
    payload: TextGenerationWorkPayload | None = None
    priority: int = 0  # Lower is higher priority (0=User, 1=Agent, 2=Background)
    runtime_id: str | None = None
    status: str = "queued"  # queued, claimed, running, completed, failed, cancelled
    created_at: datetime = field(default_factory=utc_now)
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    reservation_id: str | None = None
