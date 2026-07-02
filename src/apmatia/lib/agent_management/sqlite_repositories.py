from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from persistence import SQLiteStore
except ModuleNotFoundError:
    from apmatia.lib.persistence.persistence import SQLiteStore

from .models import Agent
from .repositories import AgentRepository
from .prompt_repositories import AgentPromptManagementTables, SQLiteAgentPromptRepository


@dataclass(frozen=True, slots=True)
class AgentManagementTables:
    agents: str = "agent_management_agents"
    prompts: str = "agent_management_prompts"


class SQLiteAgentRepository(AgentRepository):
    """SQLiteStore-backed agent repository."""

    def __init__(self, store: SQLiteStore, tables: AgentManagementTables):
        self._store = store
        self._tables = tables
        self._init_schema()

    def _init_schema(self):
        """Ensure table exists (SQLiteStore creates on first insert)."""
        # SQLiteStore auto-creates tables on first insert, no explicit schema needed
        pass

    def create(self, agent: Agent) -> int:
        payload = {
            "owner_user_id": agent.owner_user_id,
            "owner_group_id": agent.owner_group_id,
            "mode": agent.mode,
            "created_at": agent.created_at.isoformat(),
            "updated_at": agent.updated_at.isoformat(),
            "name": agent.name,
            "prompt_id": agent.prompt_id,
            "system_prompt_id": agent.system_prompt_id,
            "memory_id": agent.memory_id,
            "rag_root_ids": _serialize_json(agent.rag_root_ids),
            "tool_ids": _serialize_json(agent.tool_ids),
            "default_model_id": agent.default_model_id,
            "active_model_id": agent.active_model_id,
            "metadata": _serialize_json(agent.metadata),
        }
        return self._store.insert(self._tables.agents, payload)

    def get(self, agent_id: int) -> Agent | None:
        row = self._store.get(self._tables.agents, id=agent_id)
        if row is None:
            return None
        return self._row_to_agent(row)

    def get_by_name(self, name: str) -> Agent | None:
        row = self._store.get(self._tables.agents, name=name)
        if row is None:
            return None
        return self._row_to_agent(row)

    def list_all(self) -> list[Agent]:
        rows = self._store.find(self._tables.agents)
        return [self._row_to_agent(row) for row in rows]

    def update(self, agent: Agent) -> None:
        if agent.id is None:
            raise ValueError("Cannot update agent without an id.")

        # Check if agent exists
        existing = self._store.get(self._tables.agents, id=agent.id)
        if existing is None:
            raise ValueError(f"Agent with id {agent.id} not found.")

        self._store.update(
            self._tables.agents,
            {"id": agent.id},
            {
                "owner_user_id": agent.owner_user_id,
                "owner_group_id": agent.owner_group_id,
                "mode": agent.mode,
                "created_at": agent.created_at.isoformat(),
                "updated_at": agent.updated_at.isoformat(),
                "name": agent.name,
                "prompt_id": agent.prompt_id,
                "system_prompt_id": agent.system_prompt_id,
                "memory_id": agent.memory_id,
                "rag_root_ids": _serialize_json(agent.rag_root_ids),
                "tool_ids": _serialize_json(agent.tool_ids),
                "default_model_id": agent.default_model_id,
                "active_model_id": agent.active_model_id,
                "metadata": _serialize_json(agent.metadata),
            },
        )

    def delete(self, agent_id: int) -> bool:
        deleted = self._store.delete(self._tables.agents, id=agent_id)
        return deleted > 0

    @staticmethod
    def _row_to_agent(row: dict) -> Agent:
        return Agent(
            id=int(row["id"]),
            owner_user_id=_parse_int(row.get("owner_user_id")),
            owner_group_id=_parse_int(row.get("owner_group_id")),
            mode=_parse_int(row.get("mode")) or 0,
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
            name=str(row["name"]),
            prompt_id=_parse_int(row.get("prompt_id")),
            system_prompt_id=int(row.get("system_prompt_id", 0)),
            memory_id=int(row.get("memory_id", 0)),
            rag_root_ids=_parse_json(row.get("rag_root_ids", "[]")),
            tool_ids=_parse_json(row.get("tool_ids", "[]")),
            default_model_id=_parse_int(row.get("default_model_id", row.get("default_llm_id"))),
            active_model_id=_parse_int(row.get("active_model_id")),
            metadata=_parse_json(row.get("metadata", "{}")),
        )


class SQLiteAgentManagementBundle:
    """Bundle of all SQLite repositories for agent management."""

    def __init__(self, store: SQLiteStore | str, tables: AgentManagementTables | None = None):
        self.tables = tables or AgentManagementTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.agents = SQLiteAgentRepository(self.store, self.tables)
        self.prompts = SQLiteAgentPromptRepository(self.store, AgentPromptManagementTables(prompts=self.tables.prompts))


# Helper functions

def _serialize_json(value: Any) -> str:
    """Serialize value to JSON string, or empty list if None."""
    if value is None:
        return "[]"
    import json
    return json.dumps(value, ensure_ascii=False)


def _parse_json(value: Any) -> list | dict:
    """Parse JSON string to list/dict, or empty list if None/invalid."""
    if not value:
        return []
    import json
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_int(value: Any) -> int | None:
    """Parse integer from DB value."""
    if value is None:
        return None
    return int(value)


def _parse_datetime(value: Any) -> datetime:
    """Parse a stored datetime string, defaulting to UTC now if unavailable."""
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
