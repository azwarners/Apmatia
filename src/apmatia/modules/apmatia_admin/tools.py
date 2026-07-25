from __future__ import annotations

from apmatia.core.registry import ToolContribution

TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="apmatia_admin",
        action_id="apmatia_admin.create_agent.action",
        tool_id="apmatia_create_agent",
        name="apmatia_create_agent",
        description="Create a new Apmatia agent with a full prompt configuration.",
        metadata={"builtin": True, "module": "apmatia_admin", "tool": "create_agent"},
    ),
    ToolContribution(
        module_id="apmatia_admin",
        action_id="apmatia_admin.clone_agent.action",
        tool_id="clone_agent_as",
        name="clone_agent_as",
        description="Clone an existing Apmatia agent under a new name.",
        metadata={"builtin": True, "module": "apmatia_admin", "tool": "clone_agent"},
    ),
    ToolContribution(
        module_id="apmatia_admin",
        action_id="apmatia_admin.set_agent_mode.action",
        tool_id="set_agent_mode",
        name="set_agent_mode",
        description="Switch a discussion between discussion and agentic execution modes.",
        metadata={"builtin": True, "module": "apmatia_admin", "tool": "set_agent_mode"},
    ),
]
