from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from persistence import SQLiteStore
except ModuleNotFoundError:
    from apmatia.lib.persistence.persistence import SQLiteStore

from .models import AgentToolAssignment, ToolDefinition
from .repositories import AgentToolAssignmentRepository, ToolDefinitionRepository


@dataclass(frozen=True, slots=True)
class ToolManagementTables:
    tools: str = "tool_management_tools"
    assignments: str = "tool_management_agent_assignments"


class SQLiteToolDefinitionRepository(ToolDefinitionRepository):
    def __init__(self, store: SQLiteStore, tables: ToolManagementTables):
        self._store = store
        self._tables = tables

    def create(self, tool: ToolDefinition) -> int:
        payload = {
            "owner_user_id": tool.owner_user_id,
            "owner_group_id": tool.owner_group_id,
            "mode": tool.mode,
            "created_at": tool.created_at.isoformat(),
            "updated_at": tool.updated_at.isoformat(),
            "name": tool.name,
            "description": tool.description,
            "input_schema": _serialize_json(tool.input_schema),
            "output_schema": _serialize_json(tool.output_schema),
            "provider_id": tool.provider_id,
            "enabled": tool.enabled,
            "confirmation_required": tool.confirmation_required,
            "read_only": tool.read_only,
            "metadata": _serialize_json(tool.metadata),
        }
        return self._store.insert(self._tables.tools, payload)

    def get(self, tool_id: int) -> ToolDefinition | None:
        row = self._store.get(self._tables.tools, id=tool_id)
        if row is None:
            return None
        return self._row_to_tool(row)

    def get_by_name(self, name: str) -> ToolDefinition | None:
        row = self._store.get(self._tables.tools, name=name)
        if row is None:
            return None
        return self._row_to_tool(row)

    def get_by_provider_id(self, provider_id: str) -> ToolDefinition | None:
        row = self._store.get(self._tables.tools, provider_id=provider_id)
        if row is None:
            return None
        return self._row_to_tool(row)

    def list_all(self) -> list[ToolDefinition]:
        rows = self._store.find(self._tables.tools)
        return [self._row_to_tool(row) for row in rows]

    def update(self, tool: ToolDefinition) -> None:
        if tool.id is None:
            raise ValueError("Cannot update tool without an id.")
        if self._store.get(self._tables.tools, id=tool.id) is None:
            raise ValueError(f"Tool with id {tool.id} not found.")
        self._store.update(
            self._tables.tools,
            {"id": tool.id},
            {
                "owner_user_id": tool.owner_user_id,
                "owner_group_id": tool.owner_group_id,
                "mode": tool.mode,
                "created_at": tool.created_at.isoformat(),
                "updated_at": tool.updated_at.isoformat(),
                "name": tool.name,
                "description": tool.description,
                "input_schema": _serialize_json(tool.input_schema),
                "output_schema": _serialize_json(tool.output_schema),
                "provider_id": tool.provider_id,
                "enabled": tool.enabled,
                "confirmation_required": tool.confirmation_required,
                "read_only": tool.read_only,
                "metadata": _serialize_json(tool.metadata),
            },
        )

    @staticmethod
    def _row_to_tool(row: dict[str, Any]) -> ToolDefinition:
        return ToolDefinition(
            id=int(row["id"]),
            owner_user_id=_parse_int(row.get("owner_user_id")),
            owner_group_id=_parse_int(row.get("owner_group_id")),
            mode=_parse_int(row.get("mode")) or 0,
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
            name=str(row.get("name", "")),
            description=str(row.get("description", "")),
            input_schema=_parse_json_object(row.get("input_schema", "{}")),
            output_schema=_parse_json_optional_object(row.get("output_schema")),
            provider_id=str(row.get("provider_id", "")),
            enabled=bool(row.get("enabled", True)),
            confirmation_required=bool(row.get("confirmation_required", False)),
            read_only=bool(row.get("read_only", True)),
            metadata=_parse_json_object(row.get("metadata", "{}")),
        )


class SQLiteAgentToolAssignmentRepository(AgentToolAssignmentRepository):
    def __init__(self, store: SQLiteStore, tables: ToolManagementTables):
        self._store = store
        self._tables = tables

    def upsert(self, assignment: AgentToolAssignment) -> AgentToolAssignment:
        existing = self.get_by_agent_tool(assignment.agent_id, assignment.tool_id)
        payload = {
            "agent_id": assignment.agent_id,
            "tool_id": assignment.tool_id,
            "enabled": assignment.enabled,
            "confirmation_required": assignment.confirmation_required,
            "read_only": assignment.read_only,
        }
        if existing is None:
            assignment_id = self._store.insert(self._tables.assignments, payload)
            return AgentToolAssignment(id=assignment_id, **payload)

        self._store.update(self._tables.assignments, {"id": existing.id}, payload)
        return AgentToolAssignment(id=existing.id, **payload)

    def get(self, assignment_id: int) -> AgentToolAssignment | None:
        row = self._store.get(self._tables.assignments, id=assignment_id)
        if row is None:
            return None
        return self._row_to_assignment(row)

    def get_by_agent_tool(self, agent_id: int, tool_id: int) -> AgentToolAssignment | None:
        row = self._store.get(self._tables.assignments, agent_id=agent_id, tool_id=tool_id)
        if row is None:
            return None
        return self._row_to_assignment(row)

    def list_by_agent(self, agent_id: int) -> list[AgentToolAssignment]:
        rows = self._store.find(self._tables.assignments, agent_id=agent_id)
        return [self._row_to_assignment(row) for row in rows]

    def delete(self, agent_id: int, tool_id: int) -> bool:
        deleted = self._store.delete(self._tables.assignments, agent_id=agent_id, tool_id=tool_id)
        return deleted > 0

    @staticmethod
    def _row_to_assignment(row: dict[str, Any]) -> AgentToolAssignment:
        return AgentToolAssignment(
            id=int(row["id"]),
            agent_id=int(row.get("agent_id", 0)),
            tool_id=int(row.get("tool_id", 0)),
            enabled=bool(row.get("enabled", True)),
            confirmation_required=_parse_optional_bool(row.get("confirmation_required")),
            read_only=_parse_optional_bool(row.get("read_only")),
        )


class SQLiteToolManagementBundle:
    def __init__(self, store: SQLiteStore | str, tables: ToolManagementTables | None = None):
        self.tables = tables or ToolManagementTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.tools = SQLiteToolDefinitionRepository(self.store, self.tables)
        self.assignments = SQLiteAgentToolAssignmentRepository(self.store, self.tables)


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_json_object(value: Any) -> dict[str, Any]:
    parsed = _parse_json_optional_object(value)
    return parsed or {}


def _parse_json_optional_object(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


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


def _parse_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    lowered = str(value).strip().lower()
    if lowered in {"true", "1"}:
        return True
    if lowered in {"false", "0"}:
        return False
    return None
