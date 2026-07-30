from __future__ import annotations

from unittest.mock import patch

import pytest

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.modules.preferences.commands import COMMAND_DESCRIPTORS
from apmatia.modules.preferences.module import APMATIA_PREFERENCES_MODULE
from apmatia.modules.preferences.module_views import ApmatiaPreferencesModuleViewProvider
from apmatia.modules.preferences.views import VIEW_DESCRIPTORS


def _command(verb: str):
    return next(command for command in COMMAND_DESCRIPTORS if command.metadata["verb"] == verb)


def test_module_management_is_a_preferences_view() -> None:
    view = VIEW_DESCRIPTORS[1]

    assert APMATIA_PREFERENCES_MODULE.module_id == "preferences"
    assert APMATIA_PREFERENCES_MODULE.status == "stable"
    assert APMATIA_PREFERENCES_MODULE.default_enabled is True
    assert view.view_id == "preferences.modules.view"
    assert view.metadata["view_contract_ready"] is True
    assert view.metadata["presentation"].component_type == "page"
    assert "renderer" not in view.metadata


def test_preferences_provider_lists_activation_and_catalog() -> None:
    provider = ApmatiaPreferencesModuleViewProvider()
    catalog = [{"module_id": "preferences"}]

    with patch(
        "apmatia.modules.preferences.module_views.get_module_activation",
        return_value={"show_development_modules": True},
    ), patch(
        "apmatia.modules.preferences.module_views.list_module_catalog",
        return_value=catalog,
    ) as list_catalog:
        items = provider.list_items(view=VIEW_DESCRIPTORS[1], context=ModuleViewContext(user_id=1))

    list_catalog.assert_called_once_with(include_development=True)
    assert items == [
        {
            "id": "activation",
            "item_kind": "activation",
            "name": "Enable all modules",
            "enabled": True,
            "hidden": False,
            "new_index": 0,
        },
        {
            "module_id": "preferences",
            "id": "module:preferences",
            "item_kind": "module",
            "new_index": 0,
        },
    ]


def test_preferences_provider_updates_view_order() -> None:
    provider = ApmatiaPreferencesModuleViewProvider()

    with patch(
        "apmatia.modules.preferences.module_views.set_view_order",
        return_value={"view_id": "ipe.tasks.view"},
    ) as set_order:
        result = provider.execute_command(
            command=_command("set_view_order"),
            payload={"module_id": "ipe", "view_id": "ipe.tasks.view", "new_index": 1},
            context=ModuleViewContext(user_id=1),
        )

    set_order.assert_called_once_with("ipe", "ipe.tasks.view", new_index=1)
    assert result["status"] == "updated"


@pytest.mark.parametrize(
    ("verb", "payload"),
    [
        ("set_module_visibility", {"module_id": "preferences", "hidden": True}),
        ("set_view_visibility", {"view_id": "preferences.modules.view", "hidden": True}),
    ],
)
def test_preferences_cannot_hide_module_recovery_controls(verb: str, payload: dict[str, object]) -> None:
    provider = ApmatiaPreferencesModuleViewProvider()

    with pytest.raises(ValueError, match="cannot hide itself"):
        provider.execute_command(
            command=_command(verb),
            payload=payload,
            context=ModuleViewContext(user_id=1),
        )
