from __future__ import annotations

from dataclasses import dataclass, field

from src.lib.apmatia_core.models import ApmatiaObject


MEMORY_VISIBILITIES = {"draft", "user_visible", "private"}
MEMORY_STATUSES = {"active", "archived", "deleted"}


@dataclass(slots=True)
class MemoryItem(ApmatiaObject):
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    owner_agent_id: int | None = None
    created_by_agent_id: int | None = None
    source_discussion_id: str | None = None
    source_message_ids: list[str] = field(default_factory=list)
    visibility: str = "draft"
    status: str = "active"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.title = str(self.title).strip()
        self.content = str(self.content)
        self.tags = [str(tag).strip() for tag in self.tags if str(tag).strip()]
        self.source_message_ids = [
            str(message_id).strip()
            for message_id in self.source_message_ids
            if str(message_id).strip()
        ]
        self.visibility = str(self.visibility or "draft").strip()
        self.status = str(self.status or "active").strip()
        if self.visibility not in MEMORY_VISIBILITIES:
            raise ValueError(f"Invalid memory visibility: {self.visibility}")
        if self.status not in MEMORY_STATUSES:
            raise ValueError(f"Invalid memory status: {self.status}")
