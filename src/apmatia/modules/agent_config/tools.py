from __future__ import annotations

from apmatia.core.registry import ToolContribution

TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="agent_config",
        action_id="agent_config.readme_first.action",
        tool_id="agent_config_readme_first",
        name="agent_config_readme_first",
        description="Read this first. Return the knowledge root, accepted path aliases, and usage guidance.",
        metadata={"builtin": True, "module": "agent_config", "tool": "readme_first"},
    ),
    ToolContribution(
        module_id="agent_config",
        action_id="agent_config.tree.action",
        tool_id="agent_config_tree",
        name="agent_config_tree",
        description="Return a JSON tree for the knowledge workspace.",
        metadata={"builtin": True, "module": "agent_config", "tool": "tree"},
    ),
    ToolContribution(
        module_id="agent_config",
        action_id="agent_config.read.action",
        tool_id="agent_config_read",
        name="agent_config_read",
        description="Read a UTF-8 file from the knowledge workspace.",
        metadata={"builtin": True, "module": "agent_config", "tool": "read"},
    ),
]
