from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apmatia.lib.apmatia_core.models import ApmatiaObject


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
