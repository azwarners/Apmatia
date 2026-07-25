from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry


APMATIA_RUNTIME_TELEMETRY_MODULE = ModuleMetadata(
    module_id="runtime_telemetry",
    name="Runtime Telemetry",
    version="0.1.0",
    description="Parse and summarize telemetry emitted by Apmatia model runtimes.",
    author="Nick",
    status="stable",
    category="core",
    default_enabled=True,
    tags=("telemetry", "observability", "runtime", "llama.cpp", "metrics"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_RUNTIME_TELEMETRY_MODULE)
