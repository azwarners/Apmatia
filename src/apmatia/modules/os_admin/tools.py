from __future__ import annotations

from apmatia.core.registry import ToolContribution

TOOL_DESCRIPTORS = [
    ToolContribution(
        module_id="os_admin",
        action_id="os_admin.inspect.action",
        tool_id="apmatia_os_admin",
        name="apmatia_os_admin",
        description="Run an approved read-only operating system administration command.",
        metadata={"builtin": True, "module": "os_admin", "tool": "inspect"},
    ),
]
