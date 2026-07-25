from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry


APMATIA_PERSISTENCE_MODULE = ModuleMetadata(
    module_id="persistence",
    name="Persistence",
    version="0.1.0",
    description="Provide shared SQLite, configuration, and structured log persistence infrastructure.",
    author="Nick",
    status="stable",
    category="infrastructure",
    default_enabled=True,
    tags=("persistence", "sqlite", "configuration", "logging", "storage"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_PERSISTENCE_MODULE)
