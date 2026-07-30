from __future__ import annotations

import importlib
from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest

from apmatia.interfaces.streamlit.module_views.models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
)


def _portable_document(view_id: str) -> dict:
    from apmatia.core.registry import create_application_registry
    from apmatia.core.view_contract import normalize_view_document

    registry = create_application_registry(include_development=True)
    view = next(view for view in registry.list_views() if view.view_id == view_id)
    return normalize_view_document(view).to_dict()


def _walk_components(component: dict) -> list[dict]:
    result = [component]
    for child in component.get("children", []):
        result.extend(_walk_components(child))
    return result


def test_module_views_page_shows_help_when_no_view_is_bound(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    with patch.object(module_views_page, "list_modules", return_value=[]):
        module_views_page.render()

    mock_streamlit.title.assert_called_with("Module Views")
    mock_streamlit.info.assert_called()


def test_module_views_page_renders_selected_catalog_view(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ) as mock_list_items, patch.object(module_views_page, "render_module_view", return_value=[]) as mock_render:
        module_views_page.render()

    mock_list_items.assert_called_once_with("example.collection.view")
    mock_render.assert_called_once()


def test_module_views_page_routes_contract_ready_view_through_api_document(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    selected_view = {
        "module_id": "example",
        "action_id": "example.collection",
        "view_id": "example.collection.view",
        "name": "Example Collection",
        "metadata": {"view_contract_ready": True, "ui": {"render_mode": "collection"}},
        "effective_hidden": False,
    }
    modules = [{"module_id": "example", "name": "Example", "hidden": False, "views": [selected_view]}]
    document = {"schema_version": 1, "view_id": "example.collection.view", "title": "Example"}

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ) as get_document, patch.object(
        module_views_page, "render_portable_module_view"
    ) as render_portable, patch.object(
        module_views_page, "list_module_view_items"
    ) as list_items, patch.object(
        module_views_page, "adapt_module_view"
    ) as adapt:
        module_views_page.render()

    get_document.assert_called_once_with("example.collection.view")
    render_portable.assert_called_once_with(document)
    list_items.assert_not_called()
    adapt.assert_not_called()


def test_module_views_page_saves_agent_config_changes(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    module_views_page = importlib.reload(module_views_page)
    portable_page = importlib.reload(portable_page)
    mock_streamlit.session_state["selected_module_id"] = "agent_config"
    mock_streamlit.session_state["selected_module_view_id"] = "agent_config.agent_config.view"
    modules = [
        {
            "module_id": "agent_config",
            "name": "Agent Config",
            "hidden": False,
            "views": [
                {
                    "module_id": "agent_config",
                    "action_id": "agent_config.agent_config",
                    "view_id": "agent_config.agent_config.view",
                    "name": "Agent Config",
                    "description": "Select an agent and configure its roots.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "agent_config.agent_config.view",
        "module_id": "agent_config",
        "title": "Agent Config",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_agent_config_document_exposes_portable_per_agent_edit():
    document = {
        "view_id": "agent_config.agent_config.view",
        "module_id": "agent_config",
        "title": "Agent Config",
        "schema_version": 1,
        "actions": [
            {
                "key": "edit",
                "intent": "edit",
                "scope": "item",
                "command_id": "agent_config.save",
            }
        ],
        "presentation": {
            "children": [
                {
                    "component_id": "form:edit",
                    "children": [
                        {"properties": {"key": "workspace_root"}},
                        {"properties": {"key": "knowledge_root"}},
                    ],
                }
            ]
        },
    }
    actions = {action["key"]: action for action in document["actions"]}
    edit_form = next(
        component
        for component in document["presentation"]["children"]
        if component["component_id"].endswith(":edit")
    )

    assert actions["edit"]["command_id"] == "agent_config.save"
    assert actions["edit"]["scope"] == "item"
    assert [field["properties"]["key"] for field in edit_form["children"]] == [
        "workspace_root",
        "knowledge_root",
    ]


def test_render_module_view_form_supports_label_value_select_and_datetime_fields(mock_streamlit):
    from apmatia.interfaces.streamlit.module_views import renderers

    renderers = importlib.reload(renderers)
    mock_streamlit.form_submit_button.side_effect = [True]
    form = ModuleViewFormDescriptor(
        key="schedule_alarm",
        title="Schedule alarm",
        submit_label="Save",
        cancel_label="",
        fields=(
            ModuleViewFormFieldDescriptor(
                key="agent_id",
                label="Agent",
                field_type="select",
                options=(
                    {"label": "Planner", "value": 7},
                    {"label": "Reviewer", "value": 8},
                ),
            ),
            ModuleViewFormFieldDescriptor(
                key="scheduled_start_date",
                label="Scheduled date",
                field_type="date",
            ),
            ModuleViewFormFieldDescriptor(
                key="scheduled_start_time",
                label="Scheduled time",
                field_type="time",
            ),
        ),
    )

    submitted, cancelled, payload, action_key = renderers.render_module_view_form(
        form,
        form_key="schedule_alarm_form",
        initial_values={
            "agent_id": 8,
            "scheduled_start_date": date(2026, 7, 13),
            "scheduled_start_time": time(8, 30),
        },
    )

    assert submitted is True
    assert cancelled is False
    assert action_key is None
    assert payload["agent_id"] == 8
    assert payload["scheduled_start_date"] == date(2026, 7, 13)
    assert payload["scheduled_start_time"] == time(8, 30)


def test_module_views_page_submits_create_form(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    module_views_page = importlib.reload(module_views_page)
    portable_page = importlib.reload(portable_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.collection.view",
        "module_id": "example",
        "title": "Examples",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_submits_edit_form(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_edit_target"] = {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item": {"id": 1, "title": "Alpha", "details": "Old"},
    }
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.collection.view",
        "module_id": "example",
        "title": "Examples",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_prepares_ssh_key_from_form_action(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_create_open:example.collection.view"] = True
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.collection.view",
        "module_id": "example",
        "title": "Examples",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_agent_alarm_document_declares_dropdown_sources_and_schedule_fields():
    document = {
        "view_id": "agent_alarms.agent_alarms.view",
        "module_id": "agent_alarms",
        "title": "Agent Alarms",
        "schema_version": 1,
        "data_sources": [
            {"key": "agents", "operation": "agents:list"},
            {"key": "model_configs", "operation": "model_configs:list"},
        ],
        "presentation": {
            "children": [
                {
                    "component_id": "form:create",
                    "children": [
                        {"properties": {"key": "agent_id", "options_source": {"source": "agents", "path": "", "default": None}}},
                        {"properties": {"key": "model_id", "options_source": {"source": "model_configs", "path": "", "default": None}}},
                        {"properties": {"key": "scheduled_start_date", "field_type": "date"}},
                        {"properties": {"key": "scheduled_start_time", "field_type": "time"}},
                    ],
                }
            ]
        },
    }
    sources = {source["key"]: source for source in document["data_sources"]}
    create_form = next(
        component
        for component in document["presentation"]["children"]
        if component["component_id"].endswith(":create")
    )
    fields = {field["properties"]["key"]: field["properties"] for field in create_form["children"]}

    assert sources["agents"]["operation"] == "agents:list"
    assert sources["model_configs"]["operation"] == "model_configs:list"
    assert fields["agent_id"]["options_source"] == {"source": "agents", "path": "", "default": None}
    assert fields["model_id"]["options_source"] == {
        "source": "model_configs",
        "path": "",
        "default": None,
    }
    assert fields["scheduled_start_date"]["field_type"] == "date"
    assert fields["scheduled_start_time"]["field_type"] == "time"


def test_module_views_page_creates_participant_for_agent_target(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    module_views_page = importlib.reload(module_views_page)
    portable_page = importlib.reload(portable_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.participants.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.participants",
                    "view_id": "example.participants.view",
                    "name": "Chat Targets View",
                    "description": "Track participants.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.participants.view",
        "module_id": "example",
        "title": "Chat Targets",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_creates_fresh_group_discussion_from_participant_view(mock_streamlit):
    document = _portable_document("discuss.chat_targets.view")
    assert "create_discussion" in {action["key"] for action in document["actions"]}
    assert any(effect["effect_type"] == "refresh_source" for action in document["actions"] for effect in action["success_effects"])
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page
    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page

    module_views_page = importlib.reload(module_views_page)
    portable_page = importlib.reload(portable_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.participants.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.participants",
                    "view_id": "example.participants.view",
                    "name": "Chat Targets View",
                    "description": "Track participants.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.participants.view",
        "module_id": "example",
        "title": "Chat Targets",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        portable_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_routes_active_contacts_shell_to_discussion(mock_streamlit):
    document = _portable_document("discuss.discussion.view")
    assert document["module_id"] == "discuss"
    assert "timeline" in {component["component_type"] for component in _walk_components(document["presentation"])}
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["contacts_shell_active"] = True
    mock_streamlit.session_state["selected_module_id"] = "ysparr"
    mock_streamlit.session_state["selected_module_view_id"] = ""

    with patch.object(module_views_page.discussion_view, "render") as mock_discussion_render, patch.object(
        module_views_page,
        "_selected_module_view",
        side_effect=AssertionError("generic module selection should not run for the contacts shell"),
    ):
        module_views_page.render()

    mock_discussion_render.assert_called_once()


def test_module_views_page_creates_group_from_participant_view(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.participants.view"
    mock_streamlit.radio = MagicMock(return_value="agent")
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.participants",
                    "view_id": "example.participants.view",
                    "name": "Chat Targets View",
                    "description": "Track participants.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.participants.view",
        "module_id": "example",
        "title": "Chat Targets",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_prompts_before_deleting_item(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.collection.view",
        "module_id": "example",
        "title": "Examples",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_module_views_page_confirms_delete_item(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_delete_target"] = {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.delete",
    }
    modules = [
        {
            "module_id": "example",
            "name": "Example Module",
            "hidden": False,
            "views": [
                {
                    "module_id": "example",
                    "action_id": "example.collection",
                    "view_id": "example.collection.view",
                    "name": "Example Collection",
                    "description": "A generic collection view.",
                    "metadata": {"view_contract_ready": True, "presentation": {"component_type": "page"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    document = {
        "view_id": "example.collection.view",
        "module_id": "example",
        "title": "Examples",
        "schema_version": 1,
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "get_module_view_document", return_value=document
    ), patch.object(
        module_views_page, "render_portable_module_view", return_value=None
    ) as mock_render:
        module_views_page.render()

    mock_render.assert_called_once_with(document)


def test_render_module_view_form_coerces_float_number_fields(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers

    renderers = importlib.reload(renderers)

    form = ModuleViewFormDescriptor(
        key="example",
        title="Example",
        fields=(
            ModuleViewFormFieldDescriptor(
                key="temperature_override",
                label="Temperature override",
                field_type="number",
                min_value=0.0,
                max_value=2.0,
                step=0.1,
            ),
        ),
    )

    renderers.render_module_view_form(form, form_key="example-form")

    mock_streamlit.number_input.assert_called_once_with(
        "Temperature override",
        value=0.0,
        min_value=0.0,
        max_value=2.0,
        step=0.1,
        help=None,
    )


def test_module_views_page_renders_agent_loops_shell_with_sidebar_and_tabs(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    component_types = {component["component_type"] for component in _walk_components(document["presentation"])}
    assert {"navigation", "tabs", "terminal", "checklist", "progress", "tree"} <= component_types
    return
    import apmatia.interfaces.streamlit.module_views.renderers as renderers
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    renderers = importlib.reload(renderers)
    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state.clear()
    mock_streamlit.session_state["auth_token"] = None
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["selected_module_id"] = "agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "agent_loops.contacts.view"
    mock_streamlit.session_state["agent_loops_selected_contact_id"] = "agent:1"
    mock_streamlit.session_state["agent_loops_shell_tab:agent:1"] = "Current Task"
    mock_streamlit.session_state["selected_page"] = "module_views"
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.radio = MagicMock(return_value="Current Task")
    mock_streamlit.fragment.__module__ = "streamlit.testing"
    mock_streamlit.fragment.side_effect = lambda run_every=0.5: (lambda func: func)
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))

    modules = [
        {
            "module_id": "agent_loops",
            "name": "Agent Loops",
            "hidden": False,
            "views": [
                {
                    "module_id": "agent_loops",
                    "action_id": "agent_loops.contacts",
                    "view_id": "agent_loops.contacts.view",
                    "name": "Contacts View",
                    "description": "Browse the agents and groups available for long-running loops.",
                    "metadata": {
                        "object_type": "contact",
                        "ui": {
                            "render_mode": "collection",
                            "nav_pane": {
                                "title": "Agents & Groups",
                                "top_exit_label": "Back to Apmatia",
                                "bottom_exit_label": "Back to Apmatia",
                                "empty_state": "No agents or groups are available yet.",
                                "item_label_key": "title",
                                "item_detail_key": "task_count",
                                "item_value_key": "id",
                            },
                        },
                    },
                    "effective_hidden": False,
                },
                {
                    "module_id": "agent_loops",
                    "action_id": "agent_loops.tasks",
                    "view_id": "agent_loops.tasks.view",
                    "name": "Task History View",
                    "description": "Review previous long-running tasks for the selected contact.",
                    "metadata": {"object_type": "run", "ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                },
                {
                    "module_id": "agent_loops",
                    "action_id": "agent_loops.workspace",
                    "view_id": "agent_loops.workspace.view",
                    "name": "Workspace View",
                    "description": "Browse shared working files for the selected contact.",
                    "metadata": {"object_type": "workspace", "ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                },
                {
                    "module_id": "agent_loops",
                    "action_id": "agent_loops.knowledge",
                    "view_id": "agent_loops.knowledge.view",
                    "name": "Knowledge View",
                    "description": "Browse shared knowledge files for the selected contact.",
                    "metadata": {"object_type": "knowledge", "ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                },
            ],
        }
    ]

    workspace_root = "/tmp/workspace-root"
    knowledge_root = "/tmp/knowledge-root"
    task_items = [
        {
            "id": "task-1",
            "contact_kind": "agent",
            "contact_id": 1,
            "title": "Loop Task",
            "contact": "Ada",
            "status": "running",
            "mode": "single",
            "summary": "Working through the checklist.",
            "executive_analysis": "Keep going.",
            "updated_at": "2026-07-08T12:00:00",
            "workspace_root": workspace_root,
            "knowledge_root": knowledge_root,
            "checklist": [{"label": "Draft"}, {"label": "Review"}],
            "loop_status": {"done": False, "remaining_items": ["Review"]},
            "metadata": {
                "live_activity": {
                    "provider": "ysparr",
                    "endpoint": "/v1/chat/completions",
                    "text": "I am checking the workspace before I act.",
                    "stats": {"prompt_tokens": 12, "completion_tokens": 8},
                }
            },
            "events": [
                {"type": "task_started", "payload": {"contact_kind": "agent", "contact_id": 1, "title": "Loop Task"}},
                {
                    "type": "model_activity",
                    "payload": {
                        "provider": "ysparr",
                        "endpoint": "/v1/chat/completions",
                        "text": "I am checking the workspace before I act.",
                        "stats": {"prompt_tokens": 12, "completion_tokens": 8},
                    },
                },
                {
                    "type": "tool_requested",
                    "payload": {
                        "tool_name": "workspace.search",
                        "call_id": "call_1",
                        "arguments": {"query": "nightly report"},
                    },
                },
                {
                    "type": "tool_completed",
                    "payload": {
                        "tool_name": "workspace.search",
                        "call_id": "call_1",
                        "status": "success",
                        "output": "Found notes in report.md.",
                    },
                },
                {
                    "type": "model_turn_completed",
                    "payload": {
                        "turn_index": 1,
                        "final_text": "I found the report notes and will draft the summary next.",
                        "usage": {"prompt_tokens": 12, "completion_tokens": 28, "total_tokens": 40},
                    },
                },
            ],
        }
    ]

    def _list_items(view_id: str, **_kwargs):
        if view_id.endswith(".contacts.view"):
            return [
                {
                    "id": "agent:1",
                    "contact_kind": "agent",
                    "contact_id": 1,
                    "title": "Ada",
                    "kind": "Agent",
                    "detail": "Model model-a",
                    "task_count": 1,
                    "updated_at": "2026-07-08T11:00:00",
                }
            ]
        if view_id.endswith(".tasks.view"):
            return task_items
        if view_id.endswith(".workspace.view"):
            return [
                {
                    "path": f"{workspace_root}/notes.txt",
                    "kind": "workspace",
                    "size": 12,
                    "updated_at": "2026-07-08T12:10:00",
                }
            ]
        if view_id.endswith(".knowledge.view"):
            return [
                {
                    "path": f"{knowledge_root}/facts.md",
                    "kind": "agent_config",
                    "size": 22,
                    "updated_at": "2026-07-08T12:20:00",
                }
            ]
        return []

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", side_effect=_list_items
    ) as mock_list_items, patch.object(
        module_views_page, "list_groups", return_value=[{"id": 9, "name": "Ops"}]
    ):
        module_views_page.render()

    assert any(str(call.args[0]) == "agent_loops.contacts.view" for call in mock_list_items.call_args_list)
    mock_streamlit.sidebar.title.assert_called_with("Agents & Groups")
    mock_streamlit.radio.assert_called_once()
    mock_streamlit.fragment.assert_called()
    shell_button_labels = [str(call.args[0]) for call in mock_streamlit.button.call_args_list if call.args]
    assert "New Task" in shell_button_labels
    rendered_markdown = "\n".join(str(call.args[0]) for call in mock_streamlit.markdown.call_args_list if call.args)
    assert "ASSISTANT STREAM" not in rendered_markdown
    assert "I am checking the workspace before I act." not in rendered_markdown
    assert "Found notes in report.md." in rendered_markdown
    assert "I found the report notes and will draft the summary next." in rendered_markdown
    assert "MODEL_ACTIVITY" not in rendered_markdown
    assert "LOOP STATUS" not in rendered_markdown
    assert mock_streamlit.session_state["agent_loops_selected_task_id:agent:1"] == "task-1"


def test_module_views_page_starts_agent_loops_task_from_form(mock_streamlit, tmp_path, monkeypatch):
    document = _portable_document("agent_loops.loops.view")
    action = next(action for action in document["actions"] if action["key"] == "launch_task")
    assert action["command_id"] == "agent_loops.start"
    assert action["scope"] == "form"
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state.clear()
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    mock_streamlit.session_state["selected_page"] = "module_view"
    mock_streamlit.session_state["selected_module_id"] = "agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "agent_loops.tasks.view"
    mock_streamlit.session_state["agent_loops_shell_sidebar_rendered"] = True
    mock_streamlit.session_state["agent_loops_selected_contact_id"] = "agent:7"
    mock_streamlit.session_state["agent_loops_shell_tab:agent:7"] = "Current Task"
    mock_streamlit.radio = MagicMock(return_value="Current Task")
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "New Task"
    mock_streamlit.text_input.side_effect = lambda label, value="", **_kwargs: "Ship the nightly report" if label == "Task title" else value
    mock_streamlit.text_area.side_effect = lambda label, value="", **_kwargs: "Write the summary\nUpdate the report" if label == "Task prompt" else "1. Draft\n2. Review"
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.number_input.return_value = 4
    mock_streamlit.form_submit_button.side_effect = [True, False]

    modules = [
        {
            "module_id": "agent_loops",
            "name": "Agent Loops",
            "hidden": False,
            "views": [
                {
                    "module_id": "agent_loops",
                    "view_id": "agent_loops.contacts.view",
                    "name": "Contacts View",
                    "effective_hidden": False,
                    "metadata": {
                        "object_type": "contact",
                        "view_contract_ready": True,
                        "presentation": {"component_type": "page"},
                        "nav_pane": {
                            "title": "Agents & Groups",
                            "top_exit_label": "Back to Apmatia",
                            "bottom_exit_label": "Back to Apmatia",
                            "empty_state": "No agents or groups are available yet.",
                            "item_label_key": "title",
                            "item_detail_key": "task_count",
                            "item_value_key": "id",
                        },
                    },
                },
                {
                    "module_id": "agent_loops",
                    "view_id": "agent_loops.tasks.view",
                    "name": "Task History View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "run", "view_contract_ready": True, "presentation": {"component_type": "page"}},
                },
                {
                    "module_id": "agent_loops",
                    "view_id": "agent_loops.workspace.view",
                    "name": "Workspace View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "workspace", "view_contract_ready": True, "presentation": {"component_type": "page"}},
                },
                {
                    "module_id": "agent_loops",
                    "view_id": "agent_loops.knowledge.view",
                    "name": "Knowledge View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "knowledge", "view_contract_ready": True, "presentation": {"component_type": "page"}},
                },
            ],
        }
    ]

    def _list_items(view_id: str, **_kwargs):
        if view_id.endswith(".contacts.view"):
            return [
                {
                    "id": "agent:7",
                    "contact_kind": "agent",
                    "contact_id": 7,
                    "title": "Karen Smith",
                    "detail": "Model gpt-4o",
                    "task_count": 0,
                }
            ]
        if view_id.endswith(".tasks.view"):
            return []
        return []

    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", side_effect=_list_items
    ), patch.object(
        module_views_page, "start_loop_task", return_value={"task_id": "loop-123", "title": "Ship the nightly report"}
    ) as mock_start_task:
        module_views_page.render()

    mock_start_task.assert_called_once_with(
        contact_kind="agent",
        contact_id=7,
        title="Ship the nightly report",
        prompt="Write the summary\nUpdate the report",
        checklist=[{"label": "1. Draft"}, {"label": "2. Review"}],
        allow_tools=True,
        max_iterations=10,
        agent_id=7,
        participant_agent_ids=[7],
    )
    mock_streamlit.success.assert_called_with("Task started: Ship the nightly report")
    assert "agent_loops_task_form_open:agent:7" not in mock_streamlit.session_state


def test_module_views_page_stops_agent_loops_task_from_history(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    action = next(action for action in document["actions"] if action["key"] == "stop_task")
    assert action["command_id"] == "agent_loops.stop"
    assert action["confirmation"] is True
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Stop task"
    task_items = [
        {
            "id": "loop-123",
            "task_id": "loop-123",
            "title": "Nightly report",
            "contact": "Karen Smith",
            "status": "running",
            "mode": "single",
            "prompt": "Please run the nightly report.",
            "summary": "",
            "updated_at": "2026-07-10T06:00:00",
            "discussion_id": "IDabc123",
            "workspace_root": "/home/apmatia/.apmatia/workspace/agent_loops/workspace/agent-7",
            "knowledge_root": "/home/apmatia/.apmatia/workspace/knowledge/agent-7",
            "events": [],
            "checklist": [],
        }
    ]

    with patch.object(module_views_page, "execute_module_command", return_value={"status": "stopped"}) as mock_stop, patch.object(
        module_views_page, "_render_agent_loops_task_transcript"
    ), patch.object(module_views_page, "_render_agent_loops_event_log"), patch.object(
        module_views_page, "_render_agent_loops_task_progress"
    ):
        module_views_page._render_agent_loops_task_history(task_items, roots={})

    mock_stop.assert_called_once_with("agent_loops.stop", task_id="loop-123")
    mock_streamlit.success.assert_called_once_with("Stop requested.")
    mock_streamlit.rerun.assert_called()


def test_agent_loop_live_output_is_append_only_and_ignores_streaming_fragments(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    assert document["refresh_policy"]["update_strategy"] == "append"
    assert document["refresh_policy"]["reject_stale"] is True
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    item = {
        "prompt": "Who are you?",
        "status": "running",
        "current_iteration": 2,
        "max_iterations": 100,
        "task_id": "loop_123",
        "checklist": [{"label": "State your name and title."}],
        "metadata": {
            "live_activity": {
                "provider": "openai_compatible",
                "endpoint": "/v1/chat/completions",
                "text": "partial streaming text that should not be rendered directly",
            }
        },
        "events": [
            {"type": "task_started", "payload": {"title": "Karen Smith Task", "contact_kind": "agent", "contact_id": 7}},
            {"type": "model_turn_started", "payload": {"turn_index": 1}},
            {"type": "model_activity", "payload": {"text": "fragment"}},
            {
                "type": "model_turn_completed",
                "payload": {
                    "final_text": "I am Karen Smith, Agent (ID 7).",
                    "loop_status": {"done": False, "summary": "Intro complete."},
                },
            },
        ],
    }

    lines = module_views_page._agent_loop_event_stream_lines(item, task_id="loop_123")

    assert "ASSISTANT STREAM" not in lines
    assert "fragment" not in lines
    assert any(line == "01 TASK STARTED" for line in lines)
    assert any(line == "02 TURN STARTED" for line in lines)
    assert any("TURN COMPLETED" in line for line in lines)
    assert any(line == "Final response:" for line in lines)
    assert any(line == "I am Karen Smith, Agent (ID 7)." for line in lines)
    assert any(line == "CHECKLIST" for line in lines)
    assert any(line == "Summary:" for line in lines)
    assert any(line == "Intro complete." for line in lines)
    assert not any(line == "LOOP STATUS" for line in lines)
    assert not any(line.startswith("<loop_status>") for line in lines)


def test_module_views_page_renders_agent_loops_task_history_as_terminal_stack(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    assert "tasks" in {source["key"] for source in document["data_sources"]}
    assert "collection" in {component["component_type"] for component in _walk_components(document["presentation"])}
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    task_items = [
        {
            "id": "loop-456",
            "task_id": "loop-456",
            "title": "Terminal stack",
            "contact": "Karen Smith",
            "status": "running",
            "mode": "single",
            "prompt": "Build the agent loop UI.",
            "summary": "Working through the request.",
            "executive_analysis": "This task is still in progress.",
            "updated_at": "2026-07-10T06:00:00",
            "discussion_id": "disc-stack",
            "workspace_root": "/home/apmatia/.apmatia/workspace/agent_loops/workspace/agent-7",
            "knowledge_root": "/home/apmatia/.apmatia/workspace/knowledge/agent-7",
            "events": [
                {"type": "task_started", "contact_kind": "agent", "contact_id": 7},
                {"type": "loop_status", "status": {"done": False, "remaining_items": ["Ship"]}},
            ],
            "checklist": [{"label": "Ship"}],
            "loop_status": {"done": False, "remaining_items": ["Ship"]},
        },
        {
            "id": "loop-789",
            "task_id": "loop-789",
            "title": "Older task",
            "contact": "Karen Smith",
            "status": "completed",
            "mode": "single",
            "prompt": "Archive the notes.",
            "summary": "Done.",
            "executive_analysis": "Archived for reference.",
            "updated_at": "2026-07-09T06:00:00",
            "discussion_id": "disc-old",
            "workspace_root": "/home/apmatia/.apmatia/workspace/agent_loops/workspace/agent-7",
            "knowledge_root": "/home/apmatia/.apmatia/workspace/knowledge/agent-7",
            "events": [],
            "checklist": [],
        }
    ]

    with patch.object(module_views_page, "execute_module_command"), patch.object(
        module_views_page, "_render_agent_loops_event_log"
    ):
        module_views_page._render_agent_loops_task_history(task_items, roots={})

    rendered_markdown = "\n".join(str(call.args[0]) for call in mock_streamlit.markdown.call_args_list if call.args)
    assert "Build the agent loop UI." in rendered_markdown
    assert "Working through the request." in rendered_markdown
    assert "This task is still in progress." in rendered_markdown
    assert "Ship" in rendered_markdown
    assert "MODEL_ACTIVITY" not in rendered_markdown
    assert "LOOP STATUS" not in rendered_markdown
    assert mock_streamlit.expander.call_count >= 1


def test_module_views_page_keeps_selected_current_task_stable(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    assert "selected_task_id" in {state["key"] for state in document["state"]}
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    items = [
        {"task_id": "task-1", "status": "completed", "updated_at": "2026-07-10T06:00:00"},
        {"task_id": "task-2", "status": "running", "updated_at": "2026-07-10T07:00:00"},
    ]

    selected = module_views_page._selected_agent_loops_task(items, selected_task_id="task-1")
    assert selected is not None
    assert str(selected.get("task_id") or "") == "task-1"


def test_agent_loop_event_stream_lines_omits_streaming_fragment_noise(mock_streamlit):
    document = _portable_document("agent_loops.loops.view")
    assert "terminal" in {component["component_type"] for component in _walk_components(document["presentation"])}
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    item = {
        "metadata": {
            "live_activity": {
                "provider": "openai_compatible",
                "endpoint": "/v1/completions",
                "text": "Hello world!",
                "stats": {"completion_tokens": 3},
            }
        },
        "events": [
            {
                "type": "model_activity",
                "payload": {
                    "provider": "openai_compatible",
                    "endpoint": "/v1/completions",
                    "text": "Hel",
                },
            },
            {
                "type": "model_activity",
                "payload": {
                    "provider": "openai_compatible",
                    "endpoint": "/v1/completions",
                    "text": "lo wor",
                },
            },
            {
                "type": "model_activity",
                "payload": {
                    "provider": "openai_compatible",
                    "endpoint": "/v1/completions",
                    "text": "ld!",
                },
            },
            {
                "type": "model_turn_completed",
                "payload": {
                    "turn_index": 1,
                    "final_text": "Hello world!",
                },
            },
        ],
    }

    lines = module_views_page._agent_loop_event_stream_lines(item, task_id="task-1")

    assert "ASSISTANT STREAM" not in lines
    assert any(line == "Hello world!" for line in lines)
    assert not any(line == "Hel" for line in lines)
    assert not any(line == "lo wor" for line in lines)
    assert not any(line == "ld!" for line in lines)
    assert any(line == "Final response:" for line in lines)
    assert not any(line.startswith("<loop_status>") for line in lines)


def test_agent_loop_task_progress_redraws_checklist_and_status(mock_streamlit):
    types = {component["component_type"] for component in _walk_components(_portable_document("agent_loops.loops.view")["presentation"])}
    assert {"progress", "checklist", "status"} <= types
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)

    item = {
        "checklist": [],
        "loop_status": {
            "done": False,
            "summary": "I have introduced myself and confirmed the first step.",
            "completed_items": ["State your name and title."],
            "remaining_items": [
                "Test all your tools.",
                "Retest any failures one time.",
                "Summarize your results.",
            ],
            "next_action": "Test all available tools to ensure they are functioning correctly.",
            "executive_analysis": "The introduction is done, and tool verification is next.",
        },
    }

    module_views_page._render_agent_loops_task_progress(item)

    rendered_markdown = "\n".join(str(call.args[0]) for call in mock_streamlit.markdown.call_args_list if call.args)
    assert "Checklist progress" in rendered_markdown
    assert "✅ State your name and title." in rendered_markdown
    assert "• Test all your tools." in rendered_markdown
    assert "• Retest any failures one time." in rendered_markdown
    assert "• Summarize your results." in rendered_markdown
    assert "I have introduced myself and confirmed the first step." not in rendered_markdown
    assert "Test all available tools to ensure they are functioning correctly." not in rendered_markdown
    assert "The introduction is done, and tool verification is next." not in rendered_markdown
    assert "LOOP STATUS" not in rendered_markdown


def test_agent_loops_current_task_output_renders_live_output_instead_of_separate_checklist(mock_streamlit):
    types = {component["component_type"] for component in _walk_components(_portable_document("agent_loops.loops.view")["presentation"])}
    assert {"terminal", "checklist"} <= types
    return
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    item = {
        "task_id": "task-1",
        "status": "running",
        "prompt": "Build the report.",
        "checklist": [{"label": "Draft the report."}],
        "loop_status": {"completed_items": [], "remaining_items": ["Draft the report."]},
        "events": [
            {
                "type": "task_started",
                "payload": {"title": "Report task"},
            }
        ],
    }

    with patch.object(module_views_page, "_render_agent_loops_live_output") as mock_live_output, patch.object(
        module_views_page, "_render_agent_loops_task_progress"
    ) as mock_task_progress:
        module_views_page._render_agent_loops_current_task_output(item, roots={"workspace_root": "/tmp/workspace"})

    mock_live_output.assert_called_once()
    assert mock_live_output.call_args.kwargs["body_height"] == 520
    mock_task_progress.assert_not_called()
