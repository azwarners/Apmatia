"""Integration tests for memory tool execution against SQLite-backed stores."""

from __future__ import annotations

import tempfile
from pathlib import Path

from apmatia.lib.agent_management.module import AgentManager
from apmatia.lib.agent_management.sqlite_repositories import SQLiteAgentManagementBundle
from apmatia.modules.memory_manager.manager import MemoryManager
from apmatia.modules.memory_manager.sqlite_repositories import SQLiteMemoryManagementBundle
from apmatia.modules.memory_manager.tooling import build_memory_tool_providers, memory_tool_definitions
from apmatia.modules.agent_tools.manager import ToolManager
from apmatia.modules.agent_tools.models import ToolCall
from apmatia.modules.agent_tools.sqlite_repositories import SQLiteToolManagementBundle


def _temp_db_path() -> str:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    return handle.name


def test_memory_tools_isolate_memories_per_agent():
    db_path = _temp_db_path()
    try:
        agent_bundle = SQLiteAgentManagementBundle(db_path)
        memory_bundle = SQLiteMemoryManagementBundle(db_path)
        tool_bundle = SQLiteToolManagementBundle(db_path)

        agent_manager = AgentManager(agent_bundle.agents, agent_bundle.prompts)
        memory_manager = MemoryManager(memory_bundle.memories)
        tool_manager = ToolManager(
            tool_bundle.tools,
            tool_bundle.assignments,
            agent_manager,
            builtin_providers=build_memory_tool_providers(memory_manager, agent_manager),
            builtin_definitions=memory_tool_definitions(),
        )

        agent_one = agent_manager.create_agent("Agent One", owner_user_id=1)
        agent_two = agent_manager.create_agent("Agent Two", owner_user_id=1)

        create_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_create")
        search_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_search")
        get_tool = next(tool for tool in tool_manager.list_tool_definitions() if tool.name == "memory_get")
        for agent_id in (agent_one.id, agent_two.id):
            tool_manager.assign_tool_to_agent(int(agent_id), int(create_tool.id))
            tool_manager.assign_tool_to_agent(int(agent_id), int(search_tool.id))
            tool_manager.assign_tool_to_agent(int(agent_id), int(get_tool.id))

        created_one = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=int(create_tool.id),
                requester_agent_id=int(agent_one.id),
                arguments={"title": "Agent One note", "content": "Alpha"},
            )
        )
        created_two = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=int(create_tool.id),
                requester_agent_id=int(agent_two.id),
                arguments={"title": "Agent Two note", "content": "Beta"},
            )
        )
        available_one = [tool.name for tool in tool_manager.list_tools_available_to_agent(int(agent_one.id))]
        available_two = [tool.name for tool in tool_manager.list_tools_available_to_agent(int(agent_two.id))]
        search_one = tool_manager.execute_tool_call(
            ToolCall(tool_id=int(search_tool.id), requester_agent_id=int(agent_one.id), arguments={"query": "note"})
        )
        search_two = tool_manager.execute_tool_call(
            ToolCall(tool_id=int(search_tool.id), requester_agent_id=int(agent_two.id), arguments={"query": "note"})
        )

        assert available_one.count("memory_create") == 1
        assert available_two.count("memory_create") == 1
        assert created_one.status == "success", created_one.error
        assert created_two.status == "success", created_two.error
        assert created_one.error is None
        assert created_two.error is None
        assert created_one.result["owner_agent_id"] == int(agent_one.id)
        assert created_two.result["owner_agent_id"] == int(agent_two.id)
        assert [item["title"] for item in search_one.result["memories"]] == ["Agent One note"]
        assert [item["title"] for item in search_two.result["memories"]] == ["Agent Two note"]
        cross_agent_get = tool_manager.execute_tool_call(
            ToolCall(
                tool_id=int(get_tool.id),
                requester_agent_id=int(agent_two.id),
                arguments={"memory_id": created_one.result["memory_id"]},
            )
        )
        assert cross_agent_get.status == "error"
        assert "Memory not found" in str(cross_agent_get.error)

        stored_one = memory_manager.get_memory(
            created_one.result["memory_id"],
            requester_user_id=1,
            requester_group_ids=set(),
        )
        stored_two = memory_manager.get_memory(
            created_two.result["memory_id"],
            requester_user_id=1,
            requester_group_ids=set(),
        )
        assert stored_one is not None and stored_one.owner_agent_id == int(agent_one.id)
        assert stored_two is not None and stored_two.owner_agent_id == int(agent_two.id)
    finally:
        Path(db_path).unlink(missing_ok=True)
