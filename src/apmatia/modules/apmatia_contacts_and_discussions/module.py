from __future__ import annotations

from apmatia.core.app_config import get_config_value, set_config_value
from apmatia.core.module_view_runtime import register_module_view_provider
from apmatia.core.registry import ModuleMetadata, Registry

from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .module_views import ApmatiaTopicManagementModuleViewProvider
from .views import VIEW_DESCRIPTORS

APMATIA_CONTACTS_AND_DISCUSSIONS_MODULE = ModuleMetadata(
    module_id="apmatia_contacts_and_discussions",
    name="Apmatia Contacts and Discussions",
    version="0.1.0",
    description="A topic-centered discussion system for organizing work, conversations, summaries, and chat targets.",
    metadata={
        "category": "knowledge-work",
        "tags": ["topics", "discussions", "summaries", "chat-targets", "turns", "migration"],
    },
)


def register(registry: Registry) -> None:
    registry.register_module(APMATIA_CONTACTS_AND_DISCUSSIONS_MODULE)
    register_module_view_provider(
        "apmatia_contacts_and_discussions",
        ApmatiaTopicManagementModuleViewProvider(),
    )
    _ensure_default_view_order()
    for action in ACTION_DESCRIPTORS:
        registry.register_action(action)
    for command in COMMAND_DESCRIPTORS:
        registry.register_command(command)
    for view in VIEW_DESCRIPTORS:
        registry.register_view(view)


def _ensure_default_view_order() -> None:
    current_orders = get_config_value("ui", "module_view_orders", default={})
    if not isinstance(current_orders, dict):
        current_orders = {}
    if "apmatia_contacts_and_discussions" in current_orders:
        return

    set_config_value(
        "ui",
        "module_view_orders",
        value={
            **current_orders,
            "apmatia_contacts_and_discussions": [
                "apmatia_contacts_and_discussions.chat_targets.view",
            ],
        },
    )


APMATIA_TOPIC_MANAGEMENT_MODULE = APMATIA_CONTACTS_AND_DISCUSSIONS_MODULE
