"""Unit tests for tool management SQLite repositories."""

import tempfile

from apmatia.modules.agent_tools.models import AgentToolAssignment, ToolDefinition
from apmatia.modules.agent_tools.sqlite_repositories import (
    SQLiteAgentToolAssignmentRepository,
    SQLiteToolDefinitionRepository,
    ToolManagementTables,
)


def _make_store(path: str):
    from apmatia.modules.persistence import SQLiteStore
    return SQLiteStore(path)


def test_tool_definition_save_and_load():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        store = _make_store(handle.name)
        tables = ToolManagementTables()
        repo = SQLiteToolDefinitionRepository(store, tables)

        tool_id = repo.create(
            ToolDefinition(
                name="custom_echo",
                description="Echo text.",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                provider_id="builtin.echo",
                enabled=True,
                confirmation_required=False,
                read_only=True,
                metadata={"kind": "demo"},
            )
        )

        retrieved = repo.get(tool_id)

        assert retrieved is not None
        assert retrieved.name == "custom_echo"
        assert retrieved.provider_id == "builtin.echo"
        assert retrieved.metadata == {"kind": "demo"}


def test_assignment_upsert_and_list():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        store = _make_store(handle.name)
        tables = ToolManagementTables()
        repo = SQLiteAgentToolAssignmentRepository(store, tables)

        created = repo.upsert(AgentToolAssignment(agent_id=7, tool_id=9, enabled=True, read_only=True))
        updated = repo.upsert(AgentToolAssignment(agent_id=7, tool_id=9, enabled=False, read_only=False))
        listed = repo.list_by_agent(7)

        assert created.id is not None
        assert updated.id == created.id
        assert len(listed) == 1
        assert listed[0].enabled is False
        assert listed[0].read_only is False
