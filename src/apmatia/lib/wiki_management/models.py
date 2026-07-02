from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from apmatia.lib.apmatia_core.models import ApmatiaObject


WIKI_NODE_TYPES = {"branch", "leaf"}


def new_wiki_id() -> str:
    return f"wiki_{uuid4().hex[:12]}"


def new_wiki_node_id() -> str:
    return f"wn_{uuid4().hex[:12]}"


@dataclass(slots=True)
class KnowledgeObject(ApmatiaObject):
    owner_agent_id: int | None = None


@dataclass(slots=True)
class Wiki(KnowledgeObject):
    title: str = ""
    description: str | None = None
    root_node_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def wiki_id(self) -> str:
        return "" if self.id is None else str(self.id)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.title = str(self.title).strip()
        if not self.title:
            raise ValueError("Wiki title cannot be empty.")
        if self.description is not None:
            clean_description = str(self.description).strip()
            self.description = clean_description or None
        self.root_node_id = str(self.root_node_id).strip()
        self.metadata = dict(self.metadata or {})


@dataclass(slots=True)
class WikiNode:
    id: str
    wiki_id: str
    parent_id: str | None
    node_type: str
    title: str
    body: str = ""
    sort_order: int = 0
    created_at: Any = None
    updated_at: Any = None

    @property
    def node_id(self) -> str:
        return str(self.id)

    def __post_init__(self) -> None:
        self.id = str(self.id).strip()
        self.wiki_id = str(self.wiki_id).strip()
        self.parent_id = None if self.parent_id in (None, "") else str(self.parent_id).strip()
        self.node_type = str(self.node_type).strip().lower()
        self.title = str(self.title).strip()
        self.body = str(self.body or "")
        self.sort_order = int(self.sort_order)
        if not self.id:
            raise ValueError("Wiki node id cannot be empty.")
        if not self.wiki_id:
            raise ValueError("Wiki node wiki_id cannot be empty.")
        if self.node_type not in WIKI_NODE_TYPES:
            raise ValueError(f"Invalid wiki node type: {self.node_type}")
        if not self.title:
            raise ValueError("Wiki node title cannot be empty.")
        if self.node_type == "branch":
            self.body = ""

