from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from apmatia.modules.persistence import SQLiteStore

from .models import MemoryItem
from .repositories import MemoryRepository


@dataclass(frozen=True, slots=True)
class MemoryManagementTables:
    memories: str = "memory_management_memories"


class SQLiteMemoryRepository(MemoryRepository):
    def __init__(self, store: SQLiteStore, tables: MemoryManagementTables):
        self._store = store
        self._tables = tables

    def create(self, memory: MemoryItem) -> int:
        payload = {
            "owner_user_id": memory.owner_user_id,
            "owner_group_id": memory.owner_group_id,
            "owner_agent_id": memory.owner_agent_id,
            "mode": memory.mode,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "title": memory.title,
            "content": memory.content,
            "tags": _serialize_json(memory.tags),
            "created_by_agent_id": memory.created_by_agent_id,
            "source_discussion_id": memory.source_discussion_id,
            "source_message_ids": _serialize_json(memory.source_message_ids),
            "visibility": memory.visibility,
            "status": memory.status,
        }
        return self._store.insert(self._tables.memories, payload)

    def get(self, memory_id: int) -> MemoryItem | None:
        row = self._store.get(self._tables.memories, id=memory_id)
        if row is None:
            return None
        return self._row_to_memory(row)

    def list_all(self) -> list[MemoryItem]:
        return [self._row_to_memory(row) for row in self._store.find(self._tables.memories)]

    def search(
        self,
        query: str,
        *,
        owner_user_id: int | None = None,
        owner_group_id: int | None = None,
        owner_agent_id: int | None = None,
        visibility: str | None = None,
        status: str | None = None,
        source_discussion_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        self._store._ensure_table(self._tables.memories)
        clauses: list[str] = []
        values: list[Any] = []
        text = query.strip()
        if text:
            like = f"%{text.lower()}%"
            clauses.append(
                "("
                "lower(coalesce(json_extract(data, '$.title'), '')) LIKE ? OR "
                "lower(coalesce(json_extract(data, '$.content'), '')) LIKE ? OR "
                "lower(coalesce(json_extract(data, '$.tags'), '')) LIKE ?"
                ")"
            )
            values.extend([like, like, like])
        if owner_user_id is not None:
            clauses.append("json_extract(data, '$.owner_user_id') = ?")
            values.append(owner_user_id)
        if owner_group_id is not None:
            clauses.append("json_extract(data, '$.owner_group_id') = ?")
            values.append(owner_group_id)
        if owner_agent_id is not None:
            clauses.append("json_extract(data, '$.owner_agent_id') = ?")
            values.append(owner_agent_id)
        if visibility is not None:
            clauses.append("json_extract(data, '$.visibility') = ?")
            values.append(visibility)
        if status is not None:
            clauses.append("json_extract(data, '$.status') = ?")
            values.append(status)
        if source_discussion_id is not None:
            clauses.append("json_extract(data, '$.source_discussion_id') = ?")
            values.append(source_discussion_id)

        query_sql = f"SELECT id, data FROM {self._tables.memories}"
        if clauses:
            query_sql += " WHERE " + " AND ".join(clauses)
        query_sql += " ORDER BY id DESC"
        if limit is not None:
            query_sql += f" LIMIT {int(limit)}"

        rows = self._store.conn.execute(query_sql, values).fetchall()
        results: list[MemoryItem] = []
        for row in rows:
            payload = json.loads(row["data"])
            if isinstance(payload, dict):
                results.append(self._row_to_memory({"id": int(row["id"]), **payload}))
        return results

    def update(self, memory: MemoryItem) -> None:
        if memory.id is None:
            raise ValueError("Cannot update memory without an id.")
        if self._store.get(self._tables.memories, id=memory.id) is None:
            raise ValueError(f"Memory with id {memory.id} not found.")
        self._store.update(
            self._tables.memories,
            {"id": memory.id},
            {
                "owner_user_id": memory.owner_user_id,
                "owner_group_id": memory.owner_group_id,
                "owner_agent_id": memory.owner_agent_id,
                "mode": memory.mode,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
                "title": memory.title,
                "content": memory.content,
                "tags": _serialize_json(memory.tags),
                "created_by_agent_id": memory.created_by_agent_id,
                "source_discussion_id": memory.source_discussion_id,
                "source_message_ids": _serialize_json(memory.source_message_ids),
                "visibility": memory.visibility,
                "status": memory.status,
            },
        )

    @staticmethod
    def _row_to_memory(row: dict[str, Any]) -> MemoryItem:
        return MemoryItem(
            id=int(row["id"]),
            owner_user_id=_parse_int(row.get("owner_user_id")),
            owner_group_id=_parse_int(row.get("owner_group_id")),
            owner_agent_id=_parse_int(row.get("owner_agent_id")),
            mode=_parse_int(row.get("mode")) or 0,
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
            title=str(row.get("title", "")),
            content=str(row.get("content", "")),
            tags=_parse_json_list(row.get("tags", "[]")),
            created_by_agent_id=_parse_int(row.get("created_by_agent_id")),
            source_discussion_id=row.get("source_discussion_id"),
            source_message_ids=_parse_json_list(row.get("source_message_ids", "[]")),
            visibility=str(row.get("visibility", "draft")),
            status=str(row.get("status", "active")),
        )


class SQLiteMemoryManagementBundle:
    def __init__(self, store: SQLiteStore | str, tables: MemoryManagementTables | None = None):
        self.tables = tables or MemoryManagementTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.memories = SQLiteMemoryRepository(self.store, self.tables)


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_json_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
