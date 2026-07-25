from __future__ import annotations

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.modules.memory_manager.manager import MemoryManager
from apmatia.modules.memory_manager.module_views import ApmatiaMemoryManagerModuleViewProvider
from apmatia.modules.memory_manager.sqlite_repositories import SQLiteMemoryManagementBundle
from apmatia.modules.agent_tools.models import ToolDefinition
from apmatia.modules.agent_tools.sqlite_repositories import SQLiteToolManagementBundle


def _command(verb: str) -> CommandContribution:
    return CommandContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        command_id=f"memory_manager.memory.{verb}",
        name=f"Memory {verb}",
        metadata={"object_type": "memory", "verb": verb, "collection_view_id": "memory_manager.memory.view"},
    )


def test_memory_manager_module_view_creates_edits_lists_and_deletes(tmp_path):
    provider = ApmatiaMemoryManagerModuleViewProvider(
        manager=MemoryManager(SQLiteMemoryManagementBundle(tmp_path / "memories.db").memories)
    )
    context = ModuleViewContext(user_id=7)
    view = ViewContribution(
        module_id="memory_manager",
        action_id="memory_manager.memory",
        view_id="memory_manager.memory.view",
        name="Memories",
        metadata={"object_type": "memory"},
    )

    created = provider.execute_command(
        command=_command("create"),
        payload={"title": "Trip note", "content": "Bring passport", "tags": "travel, packing"},
        context=context,
    )
    assert created is not None
    memory_id = created["item"]["id"]
    assert created["item"]["tags"] == ["travel", "packing"]
    assert [item["title"] for item in provider.list_items(view=view, context=context)] == ["Trip note"]

    updated = provider.execute_command(
        command=_command("edit"),
        payload={
            "item_id": memory_id,
            "title": "Trip checklist",
            "content": "Bring passport and charger",
            "tags": "travel",
            "visibility": "user_visible",
            "status": "active",
        },
        context=context,
    )
    assert updated is not None
    assert updated["item"]["title"] == "Trip checklist"

    deleted = provider.execute_command(
        command=_command("delete"),
        payload={"item_id": memory_id},
        context=context,
    )
    assert deleted is not None
    assert deleted["status"] == "deleted"
    assert provider.list_items(view=view, context=context) == []


def test_stable_mode_disables_persisted_memory_tools(tmp_path):
    from apmatia.core.tool_management_runtime import _set_memory_tool_definitions_enabled

    bundle = SQLiteToolManagementBundle(tmp_path / "tools.db")
    bundle.tools.create(
        ToolDefinition(
            name="memory_create",
            provider_id="builtin.memory_create",
            enabled=True,
            metadata={"builtin": True},
        )
    )

    _set_memory_tool_definitions_enabled(bundle.tools, development_enabled=False)
    persisted = bundle.tools.get_by_provider_id("builtin.memory_create")
    assert persisted is not None
    assert persisted.enabled is False

    _set_memory_tool_definitions_enabled(bundle.tools, development_enabled=True)
    persisted = bundle.tools.get_by_provider_id("builtin.memory_create")
    assert persisted is not None
    assert persisted.enabled is True
