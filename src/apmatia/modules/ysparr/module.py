from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry


APMATIA_YSPARR_MODULE = ModuleMetadata(
    module_id="ysparr",
    name="Ysparr",
    version="0.1.0",
    description="Backend-agnostic generative execution and persistence infrastructure.",
    author="Nick",
    status="stable",
    category="infrastructure",
    default_enabled=True,
    tags=("generative-ai", "execution", "streaming", "backends", "persistence"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_YSPARR_MODULE)
