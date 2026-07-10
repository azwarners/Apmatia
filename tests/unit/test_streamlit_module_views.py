from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

from apmatia.interfaces.streamlit.module_views.models import (
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
)


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


def test_module_views_page_submits_create_form(mock_streamlit):
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
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.collection.create"},
            ),
        ),
        create_form=ModuleViewFormDescriptor(
            key="create_example",
            title="Create example",
            submit_label="Save",
            fields=(
                ModuleViewFormFieldDescriptor(key="title", label="Title"),
            ),
        ),
    )
    create_intent = ModuleViewIntent(
        view_id="example.collection.view",
        intent="create",
        action_key="create",
        scope="view",
        payload={"command_id": "example.collection.create"},
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[create_intent]
    ), patch.object(
        module_views_page, "render_module_view_form", return_value=(True, False, {"title": "Alpha"}, None)
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "created"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.create", title="Alpha")
    assert mock_streamlit.session_state["module_view_create_open:example.collection.view"] is False
    mock_streamlit.success.assert_called_with("Item created.")
    mock_streamlit.rerun.assert_called()


def test_module_views_page_submits_edit_form(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.collection.view"
    mock_streamlit.session_state["module_view_edit_target"] = {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.edit",
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
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
        edit_form=ModuleViewFormDescriptor(
            key="edit_example",
            title="Edit example",
            submit_label="Save changes",
            fields=(
                ModuleViewFormFieldDescriptor(key="title", label="Title"),
            ),
        ),
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "title": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "render_module_view_form", return_value=(True, False, {"title": "Alpha updated"}, None)
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "updated"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.edit", item_id=1, title="Alpha updated")
    assert "module_view_edit_target" not in mock_streamlit.session_state
    mock_streamlit.success.assert_called_with("Item updated.")
    mock_streamlit.rerun.assert_called()


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
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.collection.create"},
            ),
        ),
        create_form=ModuleViewFormDescriptor(
            key="create_example",
            title="Create example",
            submit_label="Save",
            actions=(
                ModuleViewFormActionDescriptor(
                    key="prepare_ssh_key",
                    label="Generate/Prepare SSH key",
                    intent="prepare_ssh_key",
                    style="secondary",
                    payload={"command_id": "example.collection.prepare_ssh_key"},
                ),
            ),
            fields=(ModuleViewFormFieldDescriptor(key="credential_ref", label="Credential ref"),),
        ),
    )
    prepare_result = {
        "status": "prepared",
        "credential_ref": "~/.apmatia/ssh/id_ed25519",
        "private_key_path": "~/.apmatia/ssh/id_ed25519",
        "message": "SSH key prepared at ~/.apmatia/ssh/id_ed25519.",
        "ssh_public_key_install_command": "ssh-copy-id -i ~/.apmatia/ssh/id_ed25519.pub nick@192.168.86.132",
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page,
        "render_module_view_form",
        return_value=(False, False, {"credential_ref": ""}, "prepare_ssh_key"),
    ), patch.object(
        module_views_page, "execute_module_command", return_value=prepare_result
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.prepare_ssh_key", credential_ref="")
    assert mock_streamlit.session_state["module_view_create_draft:example.collection.view"]["credential_ref"] == "~/.apmatia/ssh/id_ed25519"
    assert mock_streamlit.session_state["module_view_create_notice:example.collection.view"]["message"] == "SSH key prepared at ~/.apmatia/ssh/id_ed25519."
    mock_streamlit.rerun.assert_called()


def test_module_views_page_creates_participant_for_agent_target(mock_streamlit):
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
                    "metadata": {"ui": {"render_mode": "collection", "commands": {"create": "example.participants.create"}}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.participants.view",
        title="Chat Targets",
        item_actions=(
            ModuleViewActionDescriptor(
                key="edit",
                label="Edit",
                intent="edit",
                scope="item",
                payload={"command_id": "example.participants.edit"},
            ),
        ),
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.participants.create"},
            ),
        ),
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "list_agents", return_value=[{"id": 7, "name": "Karen Smith"}]
    ), patch.object(
        module_views_page, "list_groups", return_value=[]
    ), patch.object(
        module_views_page, "list_llm_configs", return_value=[{"id": 3, "user_alias": "gpt-4o", "provider_name": "openai"}]
    ), patch.object(
        module_views_page, "list_tool_definitions", return_value=[{"id": 11, "name": "wiki.read", "provider_id": "wiki"}]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "created"}
    ) as mock_execute, patch.object(
        module_views_page, "discussion_tree", return_value={"current_discussion_id": None, "discussions": []}
    ), patch.object(
        module_views_page, "create_discussion", return_value={"discussion": {"discussion_id": "IDnew123"}}
    ) as mock_create_discussion, patch.object(
        module_views_page, "open_discussion"
    ) as mock_open_discussion:
        mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[1] if _label == "Model alias" and len(options) > 1 else options[index]
        mock_streamlit.form_submit_button.side_effect = [True, False]
        module_views_page.render()

    mock_execute.assert_called_once_with(
        "example.participants.create",
        chat_target="agent:7 - Karen Smith",
        role="agent",
        selected_model_id=3,
        temperature_override=0.0,
        tool_restrictions=[],
    )
    mock_create_discussion.assert_called_once_with(
        title="Karen Smith",
        chat_mode="single",
        agent_id=7,
        participant_agent_ids=[7],
    )
    mock_open_discussion.assert_called_once_with("IDnew123")
    assert mock_streamlit.session_state["selected_page"] == "discussion"
    assert mock_streamlit.session_state["discussion_selected_agent_id"] == 7
    mock_streamlit.success.assert_called_with("Target saved.")
    mock_streamlit.rerun.assert_called()


def test_module_views_page_opens_existing_group_discussion_from_participant_view(mock_streamlit):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state["selected_module_id"] = "example"
    mock_streamlit.session_state["selected_module_view_id"] = "example.participants.view"
    mock_streamlit.radio = MagicMock(return_value="group")
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
                    "metadata": {"ui": {"render_mode": "collection", "commands": {"create": "example.participants.create"}}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.participants.view",
        title="Chat Targets",
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.participants.create"},
            ),
        ),
    )
    tree = {
        "current_discussion_id": "IDgroup123",
        "discussions": [
            {"discussion_id": "IDgroup123", "title": "Research Team", "group_id": 9, "participant_agent_ids": []},
        ],
    }

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "list_agents", return_value=[]
    ), patch.object(
        module_views_page, "list_groups", return_value=[{"id": 9, "name": "Research Team"}]
    ), patch.object(
        module_views_page, "list_llm_configs", return_value=[]
    ), patch.object(
        module_views_page, "list_tool_definitions", return_value=[]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "created"}
    ), patch.object(
        module_views_page, "discussion_tree", return_value=tree
    ), patch.object(
        module_views_page, "open_discussion"
    ) as mock_open_discussion, patch.object(
        module_views_page, "create_discussion"
    ) as mock_create_discussion:
        mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
        mock_streamlit.form_submit_button.side_effect = [True, False]
        module_views_page.render()

    mock_create_discussion.assert_not_called()
    mock_open_discussion.assert_called_once_with("IDgroup123")
    assert mock_streamlit.session_state["selected_page"] == "discussion"
    assert mock_streamlit.session_state["discussion_selected_agent_id"] is None


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
                    "metadata": {"ui": {"render_mode": "collection", "commands": {"create": "example.participants.create"}}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.participants.view",
        title="Chat Targets",
        view_actions=(
            ModuleViewActionDescriptor(
                key="create",
                label="Create",
                intent="create",
                scope="view",
                style="primary",
                payload={"command_id": "example.participants.create"},
            ),
        ),
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "list_agents", return_value=[{"id": 7, "name": "Karen Smith"}]
    ), patch.object(
        module_views_page, "list_groups", return_value=[]
    ), patch.object(
        module_views_page, "list_llm_configs", return_value=[{"id": 3, "user_alias": "gpt-4o", "provider_name": "openai"}]
    ), patch.object(
        module_views_page, "list_tool_definitions", return_value=[]
    ), patch.object(
        module_views_page, "create_group", return_value={"status": "created"}
    ) as mock_create_group:
        mock_streamlit.form_submit_button.side_effect = [False, False, True]
        module_views_page.render()

    mock_create_group.assert_called_once_with(name="testuser", description="Be concise")
    mock_streamlit.success.assert_called_with("Group created.")
    mock_streamlit.rerun.assert_called()


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
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
        item_actions=(
            ModuleViewActionDescriptor(
                key="delete",
                label="Delete",
                intent="delete",
                scope="item",
                style="secondary",
                confirmation=True,
                payload={"command_id": "example.collection.delete"},
            ),
        ),
    )
    delete_intent = ModuleViewIntent(
        view_id="example.collection.view",
        intent="delete",
        action_key="delete",
        scope="item",
        item_id=1,
        item={"id": 1, "name": "Alpha"},
        payload={"command_id": "example.collection.delete"},
    )

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[delete_intent]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "deleted"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_not_called()
    assert mock_streamlit.session_state["module_view_delete_target"] == {
        "view_id": "example.collection.view",
        "item_id": 1,
        "item_label": "Alpha",
        "command_id": "example.collection.delete",
    }
    mock_streamlit.rerun.assert_called()


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
                    "metadata": {"ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                }
            ],
        }
    ]
    spec = CollectionViewDescriptor(
        view_id="example.collection.view",
        title="Examples",
    )
    mock_streamlit.button.side_effect = lambda label, **kwargs: label == "Delete" and kwargs.get("key") == "confirm_delete_module_view:example.collection.view:1"

    with patch.object(module_views_page, "list_modules", return_value=modules), patch.object(
        module_views_page, "list_module_view_items", return_value=[{"id": 1, "name": "Alpha"}]
    ), patch.object(module_views_page, "adapt_module_view", return_value=spec), patch.object(
        module_views_page, "render_module_view", return_value=[]
    ), patch.object(
        module_views_page, "execute_module_command", return_value={"status": "deleted"}
    ) as mock_execute:
        module_views_page.render()

    mock_execute.assert_called_once_with("example.collection.delete", item_id=1)
    assert "module_view_delete_target" not in mock_streamlit.session_state
    mock_streamlit.success.assert_called_with("Item deleted.")
    mock_streamlit.rerun.assert_called()


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


def test_module_views_page_renders_agent_loops_shell_with_sidebar_and_tabs(mock_streamlit, tmp_path, monkeypatch):
    import apmatia.interfaces.streamlit.module_views.renderers as renderers
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    renderers = importlib.reload(renderers)
    module_views_page = importlib.reload(module_views_page)
    mock_streamlit.session_state.clear()
    mock_streamlit.session_state["auth_token"] = None
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 7, "username": "testuser"}
    mock_streamlit.session_state["selected_module_id"] = "apmatia_agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "apmatia_agent_loops.contacts.view"
    mock_streamlit.session_state["agent_loops_selected_contact_id"] = "agent:1"
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
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))

    modules = [
        {
            "module_id": "apmatia_agent_loops",
            "name": "Apmatia Agent Loops",
            "hidden": False,
            "views": [
                {
                    "module_id": "apmatia_agent_loops",
                    "action_id": "apmatia_agent_loops.contacts",
                    "view_id": "apmatia_agent_loops.contacts.view",
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
                    "module_id": "apmatia_agent_loops",
                    "action_id": "apmatia_agent_loops.tasks",
                    "view_id": "apmatia_agent_loops.tasks.view",
                    "name": "Task History View",
                    "description": "Review previous long-running tasks for the selected contact.",
                    "metadata": {"object_type": "run", "ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                },
                {
                    "module_id": "apmatia_agent_loops",
                    "action_id": "apmatia_agent_loops.workspace",
                    "view_id": "apmatia_agent_loops.workspace.view",
                    "name": "Workspace View",
                    "description": "Browse shared working files for the selected contact.",
                    "metadata": {"object_type": "workspace", "ui": {"render_mode": "collection"}},
                    "effective_hidden": False,
                },
                {
                    "module_id": "apmatia_agent_loops",
                    "action_id": "apmatia_agent_loops.knowledge",
                    "view_id": "apmatia_agent_loops.knowledge.view",
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
                    "kind": "knowledge",
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

    mock_list_items.assert_any_call("apmatia_agent_loops.contacts.view")
    mock_streamlit.sidebar.title.assert_called_with("Agents & Groups")
    mock_streamlit.tabs.assert_called_once_with(["Task History", "Workspace", "Knowledge"])
    mock_streamlit.title.assert_called_with("Ada")
    assert any(str(call.args[0]).startswith("Workspace: ") for call in mock_streamlit.caption.call_args_list if call.args)
    assert any(str(call.args[0]).startswith("Knowledge: ") for call in mock_streamlit.caption.call_args_list if call.args)


def test_module_views_page_starts_agent_loops_task_from_form(mock_streamlit, tmp_path, monkeypatch):
    import apmatia.interfaces.streamlit.pages.module_views as module_views_page

    module_views_page = importlib.reload(module_views_page)
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    mock_streamlit.session_state["selected_page"] = "module_view"
    mock_streamlit.session_state["selected_module_id"] = "apmatia_agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "apmatia_agent_loops.tasks.view"
    mock_streamlit.session_state["agent_loops_shell_sidebar_rendered"] = True
    mock_streamlit.session_state["agent_loops_selected_contact_id"] = "agent:7"
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "New Task"
    mock_streamlit.text_input.side_effect = lambda label, value="", **_kwargs: "Ship the nightly report" if label == "Task title" else value
    mock_streamlit.text_area.side_effect = lambda label, value="", **_kwargs: "Write the summary\nUpdate the report" if label == "Task prompt" else "1. Draft\n2. Review"
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.number_input.return_value = 4
    mock_streamlit.form_submit_button.side_effect = [True, False]

    modules = [
        {
            "module_id": "apmatia_agent_loops",
            "name": "Apmatia Agent Loops",
            "hidden": False,
            "views": [
                {
                    "module_id": "apmatia_agent_loops",
                    "view_id": "apmatia_agent_loops.contacts.view",
                    "name": "Contacts View",
                    "effective_hidden": False,
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
                },
                {
                    "module_id": "apmatia_agent_loops",
                    "view_id": "apmatia_agent_loops.tasks.view",
                    "name": "Task History View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "run", "ui": {"render_mode": "collection"}},
                },
                {
                    "module_id": "apmatia_agent_loops",
                    "view_id": "apmatia_agent_loops.workspace.view",
                    "name": "Workspace View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "workspace", "ui": {"render_mode": "collection"}},
                },
                {
                    "module_id": "apmatia_agent_loops",
                    "view_id": "apmatia_agent_loops.knowledge.view",
                    "name": "Knowledge View",
                    "effective_hidden": False,
                    "metadata": {"object_type": "knowledge", "ui": {"render_mode": "collection"}},
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
        max_iterations=5,
        agent_id=7,
        participant_agent_ids=[7],
    )
    mock_streamlit.success.assert_called_with("Task started: Ship the nightly report")
    assert "agent_loops_task_form_open:agent:7" not in mock_streamlit.session_state


def test_module_views_page_stops_agent_loops_task_from_history(mock_streamlit):
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
            "workspace_root": "/home/apmatia/.apmatia/workspace/apmatia_agent_loops/workspace/agent-7",
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

    mock_stop.assert_called_once_with("apmatia_agent_loops.tasks.stop", task_id="loop-123")
    mock_streamlit.success.assert_called_with("Stop requested.")
    mock_streamlit.rerun.assert_called()


def test_module_views_page_renders_agent_loops_task_history_as_terminal_stack(mock_streamlit):
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
            "workspace_root": "/home/apmatia/.apmatia/workspace/apmatia_agent_loops/workspace/agent-7",
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
            "workspace_root": "/home/apmatia/.apmatia/workspace/apmatia_agent_loops/workspace/agent-7",
            "knowledge_root": "/home/apmatia/.apmatia/workspace/knowledge/agent-7",
            "events": [],
            "checklist": [],
        }
    ]

    with patch.object(
        module_views_page,
        "get_loop_task_transcript",
        return_value={
            "transcript": {
                "content": "",
                "messages": [
                    {
                        "role": "Assistant",
                        "speaker_name": "Luna Tuxamiga",
                        "text": (
                            "I am working on it.\n"
                            "<tool_call>{\"name\":\"list_agents\",\"arguments\":{}}</tool_call>\n"
                            "Done."
                        ),
                        "metadata": {
                            "prompt_cache_est_tokens": 96000,
                            "tokens_per_second": 3.04,
                        },
                    }
                ],
            }
        },
    ), patch.object(module_views_page, "execute_module_command"), patch.object(
        module_views_page, "_render_agent_loops_event_log"
    ):
        module_views_page._render_agent_loops_task_history(task_items, roots={})

    code_bodies = [str(call.args[0]) for call in mock_streamlit.code.call_args_list if call.args]
    assert code_bodies[0].startswith("PROMPT\nBuild the agent loop UI.")
    assert any("I am working on it." in body for body in code_bodies)
    assert any("Done." in body for body in code_bodies)
    assert not any("prompt_cache_est_tokens" in body for body in code_bodies)
    assert not any("tokens_per_second" in body for body in code_bodies)
    assert any("\"done\": false" in body.lower() for body in code_bodies)
    assert any("Working through the request." in body for body in code_bodies)
    assert any("This task is still in progress." in body for body in code_bodies)
    assert mock_streamlit.expander.call_count >= 2
