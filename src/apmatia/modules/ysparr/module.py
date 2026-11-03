from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry


APMATIA_YSPARR_MODULE = ModuleMetadata(
    module_id="ysparr",
    name="Ysparr",
    version="0.1.0",
    description="Authenticated adapter and Apmatia-owned Ysparr extension.",
    author="Nick",
    status="stable",
    category="infrastructure",
    default_enabled=True,
    tags=("generative-ai", "adapter", "extension", "streaming"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_YSPARR_MODULE)
