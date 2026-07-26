from __future__ import annotations

from dataclasses import replace

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution
from apmatia.modules.agent_tools.models import ToolDefinition
from apmatia.modules.agent_tools.module_views import AgentToolsModuleViewProvider
from apmatia.modules.agent_tools.views import VIEW_DESCRIPTORS


class FakeToolManager:
    def __init__(self) -> None:
        self.tools = [
            ToolDefinition(
                id=1,
                name="echo",
                description="Echo text.",
                provider_id="builtin.echo",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                metadata={"builtin": True, "module": "agent_tools"},
            )
        ]

    def list_tool_definitions(self) -> list[ToolDefinition]:
        return list(self.tools)

    def create_tool_definition(self, **payload) -> ToolDefinition:
        tool = ToolDefinition(id=2, **payload)
        self.tools.append(tool)
        return tool

    def update_tool_definition(self, tool_id: int, **payload) -> ToolDefinition:
        tool = next(item for item in self.tools if item.id == tool_id)
        updated = replace(tool, **payload)
        self.tools[self.tools.index(tool)] = updated
        return updated


def _command(verb: str) -> CommandContribution:
    return CommandContribution(
        module_id="agent_tools",
        command_id=f"agent_tools.{verb}",
        name=f"Agent Tools {verb.title()}",
        metadata={
            "verb": verb,
            "collection_view_id": "agent_tools.agent_tools.view",
        },
    )


def test_agent_tools_view_provider_lists_creates_and_edits_tool_definitions():
    manager = FakeToolManager()
    provider = AgentToolsModuleViewProvider(lambda: manager)
    context = ModuleViewContext(user_id=7)
    view = VIEW_DESCRIPTORS[0]

    assert provider.list_items(view=view, context=context)[0]["name"] == "echo"

    created = provider.execute_command(
        command=_command("create"),
        payload={
            "name": "weather",
            "description": "Get weather.",
            "provider_id": "example.weather",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "input_schema": '{"type": "object"}',
            "output_schema": '{"type": "object"}',
            "metadata": '{"source": "test"}',
        },
        context=context,
    )

    assert created["status"] == "created"
    assert manager.tools[-1].owner_user_id == 7
    assert manager.tools[-1].input_schema == {"type": "object"}

    edited = provider.execute_command(
        command=_command("edit"),
        payload={
            **created["item"],
            "item_id": 2,
            "description": "Updated weather.",
        },
        context=context,
    )

    assert edited["status"] == "updated"
    assert manager.tools[-1].description == "Updated weather."
