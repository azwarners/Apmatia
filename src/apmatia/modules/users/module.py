from __future__ import annotations

from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import UsersModuleViewProvider
from .runtime import get_group_manager, get_user_manager
from .views import VIEW_DESCRIPTORS


APMATIA_USERS_MODULE = ModuleMetadata(
    module_id="users",
    name="Users",
    version="0.1.0",
    description="Provide user, group, and membership management.",
    author="Nick",
    status="stable",
    category="infrastructure",
    default_enabled=True,
    tags=("users", "groups", "memberships", "access-control"),
    metadata={},
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_USERS_MODULE)
    register_module_view_provider(
        "users",
        UsersModuleViewProvider(
            user_manager_factory=get_user_manager,
            group_manager_factory=get_group_manager,
        ),
    )
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)
