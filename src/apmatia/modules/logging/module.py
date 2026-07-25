from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry
from apmatia.lib.persistence.logger import configure_logging

from .module_views import ApmatiaLoggingModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_LOGGING_MODULE = ModuleMetadata(
    module_id="logging",
    name="Logging",
    version="0.1.0",
    description="Structured runtime logging and a browsable log viewer for Apmatia.",
    author="Nick",
    status="stable",
    category="core",
    default_enabled=True,
    tags=("logging", "debugging", "observability", "diagnostics", "runtime"),
    metadata={
    },
)


def register(registry: Registry) -> None:
    configure_logging()
    registry.register_module(APMATIA_LOGGING_MODULE)
    register_module_view_provider("logging", ApmatiaLoggingModuleViewProvider())
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
