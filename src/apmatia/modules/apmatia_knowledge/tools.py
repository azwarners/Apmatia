from __future__ import annotations

from apmatia.core.registry import ToolContribution

TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="apmatia_knowledge",
        action_id="apmatia_knowledge.readme_first.action",
        tool_id="apmatia_knowledge_readme_first",
        name="apmatia_knowledge_readme_first",
        description="Read this first. Return the knowledge root, accepted path aliases, and usage guidance.",
        metadata={"builtin": True, "module": "apmatia_knowledge", "tool": "readme_first"},
    ),
    ToolContribution(
        module_id="apmatia_knowledge",
        action_id="apmatia_knowledge.tree.action",
        tool_id="apmatia_knowledge_tree",
        name="apmatia_knowledge_tree",
        description="Return a JSON tree for the knowledge workspace.",
        metadata={"builtin": True, "module": "apmatia_knowledge", "tool": "tree"},
    ),
    ToolContribution(
        module_id="apmatia_knowledge",
        action_id="apmatia_knowledge.read.action",
        tool_id="apmatia_knowledge_read",
        name="apmatia_knowledge_read",
        description="Read a UTF-8 file from the knowledge workspace.",
        metadata={"builtin": True, "module": "apmatia_knowledge", "tool": "read"},
    ),
]
