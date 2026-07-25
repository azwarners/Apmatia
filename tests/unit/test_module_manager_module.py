from __future__ import annotations

from unittest.mock import patch

import pytest

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.modules.module_manager.commands import COMMAND_DESCRIPTORS
from apmatia.modules.module_manager.module import APMATIA_MODULE_MANAGER_MODULE
from apmatia.modules.module_manager.module_views import ApmatiaModuleManagerViewProvider
from apmatia.modules.module_manager.views import VIEW_DESCRIPTORS


def _command(verb: str):
    return next(command for command in COMMAND_DESCRIPTORS if command.metadata["verb"] == verb)


def test_module_manager_is_a_stable_schema_selected_module_view() -> None:
    view = VIEW_DESCRIPTORS[0]

    assert APMATIA_MODULE_MANAGER_MODULE.module_id == "module_manager"
    assert APMATIA_MODULE_MANAGER_MODULE.status == "stable"
    assert APMATIA_MODULE_MANAGER_MODULE.default_enabled is True
    assert view.view_id == "module_manager.module_manager.view"
    assert view.metadata["ui"]["renderer"] == "module_manager"


def test_module_manager_provider_lists_activation_and_catalog() -> None:
    provider = ApmatiaModuleManagerViewProvider()
    catalog = [{"module_id": "module_manager"}]

    with patch(
        "apmatia.modules.module_manager.module_views.get_module_activation",
        return_value={"show_development_modules": True},
    ), patch(
        "apmatia.modules.module_manager.module_views.list_module_catalog",
        return_value=catalog,
    ) as list_catalog:
        items = provider.list_items(view=VIEW_DESCRIPTORS[0], context=ModuleViewContext(user_id=1))

    list_catalog.assert_called_once_with(include_development=True)
    assert items == [
        {
            "id": "module_catalog",
            "show_development_modules": True,
            "modules": catalog,
        }
    ]


def test_module_manager_provider_updates_view_order() -> None:
    provider = ApmatiaModuleManagerViewProvider()

    with patch(
        "apmatia.modules.module_manager.module_views.set_view_order",
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
        ("set_module_visibility", {"module_id": "module_manager", "hidden": True}),
        ("set_view_visibility", {"view_id": "module_manager.module_manager.view", "hidden": True}),
    ],
)
def test_module_manager_cannot_hide_its_recovery_controls(verb: str, payload: dict[str, object]) -> None:
    provider = ApmatiaModuleManagerViewProvider()

    with pytest.raises(ValueError, match="cannot hide itself"):
        provider.execute_command(
            command=_command(verb),
            payload=payload,
            context=ModuleViewContext(user_id=1),
        )
