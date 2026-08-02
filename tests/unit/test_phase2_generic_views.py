from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

from apmatia.core.registry import create_application_registry


CONTRACT_READY_VIEW_IDS = {
    "agent_alarms.alarms.view",
    "agent_config.agent_config.view",
    "agents.agents.view",
    "ai_host_management.hosts.view",
    "ai_host_management.resources.view",
    "agent_tools.agent_tools.view",
    "ai_model_executor.capacity.view",
    "ai_model_executor.executions.view",
    "ai_model_executor.queue.view",
    "ai_model_executor.reservations.view",
    "ai_model_executor.resources.view",
    "ai_model_manager.llm_configs.view",
    "ai_model_manager.models.view",
    "ai_model_manager.preferences.view",
    "ipe.calendar_event.view",
    "ipe.habit.view",
    "ipe.idea.view",
    "ipe.project.view",
    "ipe.task.view",
    "logging.entries.view",
    "memory_manager.memory.view",
    "preferences.modules.view",
    "preferences.preferences.view",
    "discuss.chat_targets.view",
    "discuss.discussion.view",
    "users.groups.view",
    "users.users.view",
    "worksim.org_chart_node.view",
}


def test_contract_ready_generic_view_inventory_is_exhaustive():
    registry = create_application_registry(include_development=True)
    marked = {
        view.view_id
        for view in registry.list_views()
        if bool((view.metadata or {}).get("view_contract_ready", False))
    }

    assert marked == CONTRACT_READY_VIEW_IDS


def test_generic_contract_path_has_no_compatibility_adapter_dependencies():
    import apmatia.interfaces.streamlit.module_views.contract_renderer as contract_renderer
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    sources = [
        Path(contract_renderer.__file__).read_text(encoding="utf-8"),
        Path(portable_page.__file__).read_text(encoding="utf-8"),
    ]
    for source in sources:
        assert "module_views.adapter" not in source
        assert "module_views.models" not in source
        assert "CollectionViewDescriptor" not in source
        assert "ModuleViewIntent" not in source


def test_portable_controller_executes_serialized_create_action(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    portable_page = importlib.reload(portable_page)
    document = {
        "schema_version": 1,
        "view_id": "example.items.view",
        "title": "Items",
        "data_sources": [],
        "actions": [
            {
                "key": "create",
                "intent": "create",
                "label": "Create item",
                "scope": "view",
                "command_id": "example.items.create",
                "payload": {},
                "success_effects": [{"effect_type": "refresh_source", "target": "items"}],
                "failure_effects": [],
            }
        ],
        "presentation": {"component_type": "page", "children": []},
    }
    create_event = {
        "view_id": "example.items.view",
        "intent": "create",
        "action_key": "create",
        "scope": "view",
        "item_id": None,
        "item": None,
        "payload": {"command_id": "example.items.create"},
    }

    with patch.object(portable_page, "_load_data_sources", return_value={"items": []}), patch.object(
        portable_page, "render_view_document", return_value=[create_event]
    ), patch.object(portable_page, "find_form_component", return_value={"component_type": "form"}), patch.object(
        portable_page, "render_form_component", return_value=(True, False, {"name": "Alpha"}, None)
    ), patch.object(
        portable_page, "execute_module_command", return_value={"status": "created"}
    ) as execute, patch.object(portable_page, "apply_effects", return_value=True):
        portable_page.render_portable_module_view(document)

    execute.assert_called_once_with("example.items.create", name="Alpha")
    mock_streamlit.success.assert_called_once_with("Create item completed.")
    mock_streamlit.rerun.assert_called_once()


def test_portable_controller_confirms_serialized_item_action(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    portable_page = importlib.reload(portable_page)
    document = {
        "schema_version": 1,
        "view_id": "example.items.view",
        "title": "Items",
        "data_sources": [{"key": "items", "kind": "collection", "item_key": "id"}],
        "actions": [
            {
                "key": "delete",
                "intent": "delete",
                "label": "Delete",
                "scope": "item",
                "command_id": "example.items.delete",
                "confirmation": True,
                "payload": {},
                "success_effects": [],
                "failure_effects": [],
            }
        ],
        "presentation": {"component_type": "page", "children": []},
    }
    item = {"id": 7, "name": "Alpha"}
    delete_event = {
        "view_id": "example.items.view",
        "intent": "delete",
        "action_key": "delete",
        "scope": "item",
        "item_id": "7",
        "item": item,
        "payload": {"command_id": "example.items.delete"},
    }
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Delete"

    with patch.object(portable_page, "_load_data_sources", return_value={"items": [item]}), patch.object(
        portable_page, "render_view_document", return_value=[delete_event]
    ), patch.object(
        portable_page, "execute_module_command", return_value={"status": "deleted"}
    ) as execute, patch.object(portable_page, "apply_effects", return_value=False):
        portable_page.render_portable_module_view(document)

    execute.assert_called_once_with("example.items.delete", item_id="7", item=item)
    mock_streamlit.success.assert_called_once_with("Delete completed.")


def test_portable_controller_prefills_and_executes_serialized_edit_action(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    portable_page = importlib.reload(portable_page)
    action = {
        "key": "edit",
        "intent": "edit",
        "label": "Edit",
        "scope": "item",
        "command_id": "example.items.edit",
        "payload": {},
        "success_effects": [],
        "failure_effects": [],
    }
    document = {
        "schema_version": 1,
        "view_id": "example.items.view",
        "title": "Items",
        "data_sources": [{"key": "items", "kind": "collection", "item_key": "id"}],
        "actions": [action],
        "presentation": {"component_type": "page", "children": []},
    }
    item = {"id": 7, "name": "Alpha"}
    edit_event = {
        "view_id": "example.items.view",
        "intent": "edit",
        "action_key": "edit",
        "scope": "item",
        "item_id": "7",
        "item": item,
        "payload": {"command_id": "example.items.edit"},
    }

    with patch.object(portable_page, "_load_data_sources", return_value={"items": [item]}), patch.object(
        portable_page, "render_view_document", return_value=[edit_event]
    ), patch.object(portable_page, "find_form_component", return_value={"component_type": "form"}), patch.object(
        portable_page, "render_form_component", return_value=(True, False, {"name": "Beta"}, None)
    ) as render_form, patch.object(
        portable_page, "execute_module_command", return_value={"status": "updated"}
    ) as execute, patch.object(portable_page, "apply_effects", return_value=False):
        portable_page.render_portable_module_view(document)

    assert render_form.call_args.kwargs["initial_values"] == item
    execute.assert_called_once_with("example.items.edit", name="Beta", item_id="7", item=item)


def test_portable_controller_loads_declared_module_view_data_source(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    portable_page = importlib.reload(portable_page)
    document = {
        "data_sources": [
            {
                "key": "items",
                "kind": "collection",
                "operation": "module_view_items:example.items.view",
                "error_text": "Items unavailable.",
            }
        ]
    }
    with patch.object(
        portable_page,
        "list_module_view_items",
        return_value=[{"id": 1, "name": "Alpha"}],
    ) as load_items:
        sources = portable_page._load_data_sources(document)

    assert sources == {"items": [{"id": 1, "name": "Alpha"}]}
    load_items.assert_called_once_with("example.items.view")
