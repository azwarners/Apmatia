from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import apmatia.core.wiki_management_runtime as wiki_runtime
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.modules.worksim.actions import ACTION_DESCRIPTORS
from apmatia.modules.worksim.commands import COMMAND_DESCRIPTORS
from apmatia.modules.worksim.collections import ORG_CHART_VIEW_SPECS
from apmatia.modules.worksim.module import APMATIA_WORKSIM_MODULE, register
from apmatia.modules.worksim.module_views import ApmatiaWorksimModuleViewProvider
from apmatia.modules.worksim.views import VIEW_DESCRIPTORS


def test_worksim_module_registers_module_metadata_and_views():
    registry = Registry()

    register(registry)

    assert registry.list_modules(include_development=True) == [APMATIA_WORKSIM_MODULE]
    assert [action.action_id for action in registry.list_actions()] == sorted(
        action.action_id for action in ACTION_DESCRIPTORS
    )
    assert [command.command_id for command in registry.list_commands()] == sorted(
        command.command_id for command in COMMAND_DESCRIPTORS
    )
    assert [command.path for command in registry.list_commands()] == [
        tuple(command.command_id.split(".")) for command in registry.list_commands()
    ]
    assert [view.view_id for view in registry.list_views()] == sorted(view.view_id for view in VIEW_DESCRIPTORS)


def test_worksim_org_chart_provider_creates_and_updates_tree(tmp_path: Path):
    provider = ApmatiaWorksimModuleViewProvider()

    wiki_runtime._bundle = None
    wiki_runtime._wiki_manager = None
    try:
        with patch.object(wiki_runtime, "APP_DIR", tmp_path / "app"), patch.object(
            wiki_runtime, "DATA_DIR", tmp_path / "data"
        ), patch.object(wiki_runtime, "WIKI_DB_PATH", tmp_path / "data" / "wikis.db"):
            manager = wiki_runtime.get_wiki_manager()

        with patch("apmatia.modules.worksim.module_views.get_wiki_manager", return_value=manager):
            view = VIEW_DESCRIPTORS[0]
            list_items = provider.list_items(view=view, context=ModuleViewContext(user_id=7))
            assert len(list_items) == 1
            assert list_items[0]["title"] == "User"
            assert list_items[0]["is_root"] is True

            create_command = next(command for command in COMMAND_DESCRIPTORS if command.metadata.get("verb") == "create")
            edit_command = next(command for command in COMMAND_DESCRIPTORS if command.metadata.get("verb") == "edit")
            delete_command = next(command for command in COMMAND_DESCRIPTORS if command.metadata.get("verb") == "delete")

            created = provider.execute_command(
                command=create_command,
                payload={"title": "Engineering Lead", "node_type": "branch"},
                context=ModuleViewContext(user_id=7),
            )
            assert created is not None
            assert created["status"] == "created"
            created_item = created["item"]
            assert created_item["title"] == "Engineering Lead"
            assert created_item["parent_id"] is not None

            updated = provider.execute_command(
                command=edit_command,
                payload={"item_id": created_item["id"], "title": "Engineering Director"},
                context=ModuleViewContext(user_id=7),
            )
            assert updated is not None
            assert updated["status"] == "updated"
            assert updated["item"]["title"] == "Engineering Director"

            deleted = provider.execute_command(
                command=delete_command,
                payload={"item_id": created_item["id"]},
                context=ModuleViewContext(user_id=7),
            )
            assert deleted is not None
            assert deleted["status"] == "deleted"

            final_items = provider.list_items(view=view, context=ModuleViewContext(user_id=7))
            assert [item["title"] for item in final_items] == ["User"]
    finally:
        wiki_runtime._bundle = None
        wiki_runtime._wiki_manager = None


def test_worksim_collection_specs_define_org_chart_metadata_without_streamlit():
    assert [spec.object_type for spec in ORG_CHART_VIEW_SPECS] == ["org_chart_node"]
    spec = ORG_CHART_VIEW_SPECS[0]
    assert spec.view_id.endswith(".view")
    assert spec.list_command_id.endswith(".list")
    assert spec.create_command_id.endswith(".create")
    assert spec.edit_command_id.endswith(".edit")
    assert spec.delete_command_id.endswith(".delete")
    assert spec.metadata["ui"]["render_mode"] == "collection"
