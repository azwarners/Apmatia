from __future__ import annotations

from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .views import VIEW_DESCRIPTORS


APMATIA_AUTH_MODULE = ModuleMetadata(
    module_id="auth",
    name="Authentication",
    version="0.1.0",
    description="Provide authentication sessions and the Apmatia login view.",
    author="Nick",
    status="stable",
    category="infrastructure",
    default_enabled=True,
    tags=("authentication", "sessions", "login", "access-control"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_AUTH_MODULE)
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
