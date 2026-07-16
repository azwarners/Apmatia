from __future__ import annotations

from apmatia.core.registry import ToolContribution

TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="source_inspection",
        action_id="source_inspection.tree.action",
        tool_id="apmatia_tree",
        name="apmatia_tree",
        description="Return a JSON tree for a directory.",
        metadata={"builtin": True, "library": "source_inspection", "tool": "tree"},
    ),
    ToolContribution(
        module_id="source_inspection",
        action_id="source_inspection.read.action",
        tool_id="apmatia_read",
        name="apmatia_read",
        description="Read a source file with metadata and truncation.",
        metadata={"builtin": True, "library": "source_inspection", "tool": "read_file"},
    ),
    ToolContribution(
        module_id="source_inspection",
        action_id="source_inspection.trace_import.action",
        tool_id="apmatia_trace_import",
        name="apmatia_trace_import",
        description="Trace imports and detect dependency cycles.",
        metadata={"builtin": True, "library": "source_inspection", "tool": "trace_import"},
    ),
]
