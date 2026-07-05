from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from apmatia.lib.apmatia_core.models import utc_now


CONNECTION_TYPES = {"local", "ssh"}


@dataclass(slots=True)
class AIHost:
    id: int | None = None
    name: str = ""
    hostname: str = ""
    role: str = ""
    connection_type: str = "local"
    username: str = ""
    port: int = 22
    credential_ref: str = ""
    enabled: bool = True
    notes: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.hostname = str(self.hostname).strip()
        self.role = str(self.role).strip()
        self.connection_type = str(self.connection_type or "local").strip().lower()
        self.username = str(self.username).strip()
        self.credential_ref = str(self.credential_ref).strip()
        self.notes = str(self.notes).strip()
        self.port = int(self.port)
        self.enabled = bool(self.enabled)
        if self.connection_type not in CONNECTION_TYPES:
            raise ValueError(f"Invalid connection type: {self.connection_type}")
        if not self.name:
            raise ValueError("name is required for an AI host.")
        if not self.hostname:
            raise ValueError("hostname is required for an AI host.")
        if not self.role:
            raise ValueError("role is required for an AI host.")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("port must be between 1 and 65535.")
        if self.connection_type == "ssh" and not self.username:
            raise ValueError("username is required for SSH hosts.")


@dataclass(slots=True)
class HostResourceSnapshot:
    total_ram_bytes: int = 0
    available_ram_bytes: int = 0
    swap_total_bytes: int = 0
    swap_free_bytes: int = 0
    vram_total_bytes: int | None = None
    vram_free_bytes: int | None = None
    detected_gpus: list[dict[str, object]] = field(default_factory=list)
    collection_timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class AIHostResourceReport:
    host_id: int | None = None
    name: str = ""
    hostname: str = ""
    role: str = ""
    connection_type: str = "local"
    username: str = ""
    port: int = 22
    credential_ref: str = ""
    enabled: bool = True
    notes: str = ""
    resource_status: str = "unknown"
    resource_error: str = ""
    total_ram_bytes: int = 0
    available_ram_bytes: int = 0
    swap_total_bytes: int = 0
    swap_free_bytes: int = 0
    vram_total_bytes: int | None = None
    vram_free_bytes: int | None = None
    detected_gpu_count: int = 0
    detected_gpu_summary: str = ""
    detected_gpus: list[dict[str, object]] = field(default_factory=list)
    collection_timestamp: datetime = field(default_factory=utc_now)
