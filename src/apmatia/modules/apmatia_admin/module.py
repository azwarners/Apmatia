from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .tools import TOOL_DESCRIPTORS

APMATIA_ADMIN_MODULE = ModuleMetadata(
    module_id="apmatia_admin",
    name="Apmatia Admin",
    version="0.1.0",
    description="Tools for administering Apmatia agents.",
    author="Nick",
    status="development",
    category="core",
    default_enabled=True,
    tags=("apmatia", "administration", "agents"),
    metadata={
        "provider_ids": [
            "builtin.apmatia_create_agent",
            "builtin.apmatia_clone_agent_as",
        ],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_ADMIN_MODULE)
    for tool in TOOL_DESCRIPTORS:
        registry.register_tool(tool)
