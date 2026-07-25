from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .tooling import OS_ADMIN_PROVIDER_ID
from .tools import TOOL_DESCRIPTORS

APMATIA_OS_ADMIN_MODULE = ModuleMetadata(
    module_id="os_admin",
    name="OS Admin",
    version="0.1.0",
    description="Read-only operating system administration and diagnostic tools.",
    author="Nick",
    status="development",
    category="infrastructure",
    default_enabled=True,
    tags=("operating-system", "administration", "diagnostics", "inspection"),
    metadata={"provider_ids": [OS_ADMIN_PROVIDER_ID]},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_OS_ADMIN_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
