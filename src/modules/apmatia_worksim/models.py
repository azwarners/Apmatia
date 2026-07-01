from __future__ import annotations

from dataclasses import dataclass
@dataclass(slots=True)
class WorksimOrgChartEntry:
    id: str
    wiki_id: str
    parent_id: str | None
    node_type: str
    title: str
    body: str = ""
    sort_order: int = 0
    depth: int = 0
    path: str = ""
    owner_user_id: int | None = None
    owner_agent_id: int | None = None
    is_root: bool = False
