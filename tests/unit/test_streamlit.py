"""Tests for the Streamlit interface."""
import importlib
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from apmatia.api.http.routes.settings_routes import SettingsPayload

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_show_auth_form_returns_true_when_api_session_is_authenticated(mock_streamlit):
    """Auth form short-circuits when the API session is already active."""
    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        return_value={"authenticated": True, "username": "testuser"},
    ):
        import apmatia.interfaces.streamlit.pages.login as login_page

        login_page = importlib.reload(login_page)
        result = login_page.show_auth_form()

    assert result is True
    assert mock_streamlit.session_state["auth_token"] == "api-session"
    assert mock_streamlit.session_state["authenticated_user"]["username"] == "testuser"


def test_show_auth_form_logs_in_via_api(mock_streamlit):
    """Sign-in uses the API client rather than talking to core directly."""
    mock_streamlit.form_submit_button.side_effect = [True, False]

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        side_effect=[
            {"authenticated": False, "has_users": True},
            {"authenticated": True, "user_id": 7, "username": "testuser"},
        ],
    ), patch(
        "apmatia.interfaces.streamlit.api_client.login",
        return_value={"status": "authenticated", "username": "testuser"},
    ) as mock_login:
        import apmatia.interfaces.streamlit.pages.login as login_page

        login_page = importlib.reload(login_page)
        result = login_page.show_auth_form()

    assert result is False
    mock_streamlit.form.assert_any_call("apmatia_signin_form")
    mock_streamlit.form_submit_button.assert_any_call("Sign In")
    mock_login.assert_called_once_with("testuser", "testuser")
    assert mock_streamlit.session_state["authenticated_user"]["user_id"] == 7
    assert mock_streamlit.session_state["authenticated_user"]["username"] == "testuser"
    mock_streamlit.success.assert_called_with("Welcome back, testuser!")
    mock_streamlit.rerun.assert_called_once()


def test_api_client_hydrates_cookie_from_browser_context(mock_streamlit):
    """The Streamlit API client restores auth from a browser cookie on refresh."""
    mock_streamlit.session_state["api_cookies"] = {}
    mock_streamlit.context.cookies = {"apmatia_session": "browser-token"}

    class FakeCookies(dict):
        def set(self, key, value):
            self[key] = value

    class FakeResponse:
        status_code = 200
        content = b'{"authenticated": true, "username": "testuser"}'

        @staticmethod
        def json():
            return {"authenticated": True, "username": "testuser"}

    mock_client = type("FakeClient", (), {})()
    mock_client.cookies = FakeCookies()
    mock_client.request = MagicMock(return_value=FakeResponse())

    mock_test_client = MagicMock()
    mock_test_client.return_value.__enter__.return_value = mock_client
    mock_test_client.return_value.__exit__.return_value = False

    import apmatia.interfaces.streamlit.api_client as api_client

    api_client = importlib.reload(api_client)

    with patch.object(api_client, "create_app", return_value=MagicMock()), patch.object(
        api_client, "TestClient", mock_test_client
    ):
        result = api_client.get_auth_session()

    assert result["authenticated"] is True
    assert mock_streamlit.session_state["api_cookies"]["apmatia_session"] == "browser-token"
    mock_streamlit.html.assert_called()
    assert mock_client.cookies["apmatia_session"] == "browser-token"


def test_settings_page_loads_and_saves(mock_streamlit):
    """Settings page loads grouped values and posts them back through the API."""
    current_settings = {
        "llama_server_log_dir": "/var/log/llama.cpp",
        "gguf_directories": "/models/gguf\n/alt/models/gguf",
        "gguf_directory": "/models/gguf",
        "auto_scan_gguf_directory": True,
        "llama_server_executable_path": "/usr/bin/llama-server",
        "llama_server_default_args": "--ctx-size 4096\n--host 0.0.0.0",
        "workspace_root": "/home/nick/.apmatia/workspace",
        "knowledge_root": "/home/nick/.apmatia/knowledge",
        "timezone": "America/Phoenix",
        "theme": "dark",
        "font_family": "system-ui",
        "accent_color": "#ff6b6b",
        "font_size": 16,
        "title_bar_height": 56,
        "title_bar_font_size": 20,
    }
    text_values = {
        "llama.cpp log directory": "/var/log/llama.cpp",
        "Font family": "system-ui",
        "GGUF models directory": "/models/gguf",
        "llama-server executable": "/usr/bin/llama-server",
        "llama-server default args": "--ctx-size 4096\n--host 0.0.0.0",
    }
    mock_streamlit.text_input.side_effect = (
        lambda label, value="", **_kwargs: text_values.get(label, value)
    )
    mock_streamlit.text_area.side_effect = (
        lambda _label, value="", **_kwargs: value
    )
    mock_streamlit.checkbox.side_effect = lambda _label, value=False, **_kwargs: value
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.color_picker.side_effect = lambda _label, value="#ff6b6b", **_kwargs: value
    mock_streamlit.slider.side_effect = lambda _label, min_value=0, max_value=100, value=0, **_kwargs: value
    mock_streamlit.form_submit_button.side_effect = [True, False]

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_settings",
        return_value=current_settings,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.save_settings",
    ) as mock_save:
        import apmatia.interfaces.streamlit.pages.settings as settings_page

        settings_page = importlib.reload(settings_page)
        settings_page.render()
        settings_page.render()

    mock_save.assert_called_once()
    payload = mock_save.call_args.args[0]
    assert isinstance(payload, SettingsPayload)
    assert payload.llama_server_log_dir == "/var/log/llama.cpp"
    assert payload.gguf_directories == "/models/gguf\n/alt/models/gguf"
    assert payload.gguf_directory == ""
    assert payload.auto_scan_gguf_directory is True
    assert payload.llama_server_executable_path == "/usr/bin/llama-server"
    assert payload.llama_server_default_args == "--ctx-size 4096\n--host 0.0.0.0"
    assert payload.workspace_root == "/home/nick/.apmatia/workspace"
    assert payload.knowledge_root == "/home/nick/.apmatia/knowledge"
    assert payload.timezone == "America/Phoenix"
    assert payload.theme == "dark"
    assert any(c.args[:1] == ("Current local time",) for c in mock_streamlit.metric.call_args_list)
    assert any(c.args[:1] == ("Current UTC",) for c in mock_streamlit.metric.call_args_list)
    mock_streamlit.success.assert_called_with("Settings saved.")


def test_agent_management_page_loads_creates_and_lists(mock_streamlit):
    """Agent management page uses the API client for CRUD and LLM selection."""
    agents = [
        {
            "id": 1,
            "name": "Planner",
            "prompt_id": 17,
            "system_prompt_id": 7,
            "memory_id": 11,
            "rag_root_ids": [101, 102],
            "tool_ids": [201],
            "default_model_id": 301,
            "active_model_id": 302,
            "metadata": {"team": "ops"},
        }
    ]
    llm_configs = [
        {"id": 301, "name": "Default", "model_name": "gpt-4o-mini"},
        {"id": 302, "name": "Active", "model_name": "gpt-4o"},
    ]
    mock_streamlit.session_state["agent_selected_id"] = 1
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value or "Planner"
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Available tool":
            return next(option for option in options if option.get("provider_id") == "builtin.echo")
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_compiled_agent_prompt",
        return_value="You are Planner.",
    ) as mock_compiled_prompt, patch(
        "apmatia.interfaces.streamlit.api_client.get_agent_prompt",
        return_value=None,
    ), patch("apmatia.interfaces.streamlit.api_client.create_agent") as mock_create, patch(
        "apmatia.interfaces.streamlit.api_client.update_agent"
    ) as mock_update, patch(
        "apmatia.interfaces.streamlit.api_client.delete_agent"
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.agent_management as agent_management_page

        agent_management_page = importlib.reload(agent_management_page)
        agent_management_page.render()

    mock_create.assert_not_called()
    mock_update.assert_not_called()
    mock_delete.assert_not_called()
    mock_compiled_prompt.assert_called_once_with(17, name="Planner")
    mock_streamlit.title.assert_called_with("Agent Management")
    mock_streamlit.caption.assert_any_call(
        "Create, edit, and remove Agent objects through the local API."
    )


def test_agent_management_clone_button_prefills_new_agent_form(mock_streamlit):
    """Clone selected agent loads a new draft agent into the editor."""
    agents = [
        {
            "id": 1,
            "name": "Planner",
            "prompt_id": 17,
            "system_prompt_id": 7,
            "memory_id": 11,
            "rag_root_ids": [101, 102],
            "tool_ids": [201],
            "default_model_id": 301,
            "active_model_id": 302,
            "metadata": {"team": "ops"},
            "owner_user_id": 9,
            "owner_group_id": None,
        }
    ]
    llm_configs = [
        {"id": 301, "name": "Default", "model_name": "gpt-4o-mini"},
        {"id": 302, "name": "Active", "model_name": "gpt-4o"},
    ]
    mock_streamlit.session_state["agent_selected_id"] = 1
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value or "Planner"
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Clone selected agent"

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_compiled_agent_prompt",
        return_value="You are Planner.",
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_agent_prompt",
        return_value={
            "personality": "Warm and practical.",
            "skills": "Planning and memory work.",
        },
    ), patch("apmatia.interfaces.streamlit.api_client.create_agent") as mock_create, patch(
        "apmatia.interfaces.streamlit.api_client.update_agent"
    ) as mock_update, patch(
        "apmatia.interfaces.streamlit.api_client.delete_agent"
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.agent_management as agent_management_page

        agent_management_page = importlib.reload(agent_management_page)
        agent_management_page.render()

    mock_create.assert_not_called()
    mock_update.assert_not_called()
    mock_delete.assert_not_called()
    assert mock_streamlit.session_state["agent_form_values"]["id"] is None
    assert mock_streamlit.session_state["agent_form_values"]["prompt_id"] is None
    assert mock_streamlit.session_state["agent_form_values"]["name"] == "Copy of Planner"
    assert mock_streamlit.session_state["agent_form_values"]["owner_user_id"] == 9
    assert mock_streamlit.session_state["agent_form_values"]["memory_id"] == 11
    assert mock_streamlit.session_state["agent_selected_id"] == 1


def test_agent_management_delete_requires_confirmation(mock_streamlit):
    agents = [
        {
            "id": 1,
            "name": "Planner",
            "prompt_id": 17,
            "system_prompt_id": 7,
            "memory_id": 11,
            "rag_root_ids": [],
            "tool_ids": [],
            "default_model_id": None,
            "active_model_id": None,
            "metadata": {},
        }
    ]
    mock_streamlit.session_state["agent_selected_id"] = 1
    mock_streamlit.session_state["agent_form_values"] = {"id": 1, "name": "Planner", "prompt_id": 17}
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Available tool":
            return next(option for option in options if option.get("provider_id") == "builtin.echo")
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Delete selected agent"

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=[]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_compiled_agent_prompt",
        return_value="You are Planner.",
    ), patch(
        "apmatia.interfaces.streamlit.api_client.delete_agent",
        return_value=True,
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.agent_management as agent_management_page

        agent_management_page = importlib.reload(agent_management_page)
        agent_management_page.render()

    mock_delete.assert_not_called()
    assert mock_streamlit.session_state["agent_delete_target"] == {"id": 1, "name": "Planner"}
    assert mock_streamlit.session_state["agent_selected_id"] == 1
    assert mock_streamlit.session_state["agent_form_values"]["id"] == 1
    mock_streamlit.rerun.assert_called()


def test_agent_management_confirmed_delete_clears_selected_form_state(mock_streamlit):
    agents = [
        {
            "id": 1,
            "name": "Planner",
            "prompt_id": 17,
            "system_prompt_id": 7,
            "memory_id": 11,
            "rag_root_ids": [],
            "tool_ids": [],
            "default_model_id": None,
            "active_model_id": None,
            "metadata": {},
        }
    ]
    mock_streamlit.session_state["agent_selected_id"] = 1
    mock_streamlit.session_state["agent_form_values"] = {"id": 1, "name": "Planner", "prompt_id": 17}
    mock_streamlit.session_state["agent_delete_target"] = {"id": 1, "name": "Planner"}
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value

    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Available tool":
            return next(option for option in options if option.get("provider_id") == "builtin.echo")
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda label, **kwargs: label == "Delete" and kwargs.get("key") == "confirm_delete_agent_1"

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=[]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_compiled_agent_prompt",
        return_value="You are Planner.",
    ), patch(
        "apmatia.interfaces.streamlit.api_client.delete_agent",
        return_value=True,
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.agent_management as agent_management_page

        agent_management_page = importlib.reload(agent_management_page)
        agent_management_page.render()

    mock_delete.assert_called_once_with(1)
    assert mock_streamlit.session_state["agent_form_values"]["id"] is None
    assert mock_streamlit.session_state["agent_selected_id"] is None
    assert "agent_delete_target" not in mock_streamlit.session_state
    mock_streamlit.success.assert_any_call("Agent deleted.")
    mock_streamlit.rerun.assert_called()


def test_tool_management_page_executes_safe_tool_calls(mock_streamlit):
    """Tool management page loads definitions and executes a selected safe tool through the API."""
    agents = [{"id": 7, "name": "Planner"}]
    tools = [
        {
            "id": 0,
            "name": "apmatia_create_agent",
            "description": "Create a new Apmatia agent",
            "provider_id": "builtin.apmatia_create_agent",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        },
        {
            "id": 1,
            "name": "echo",
            "description": "Echo tool",
            "provider_id": "builtin.echo",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        }
    ]
    assignments = [
        {
            "id": 10,
            "agent_id": 7,
            "tool_id": 1,
            "enabled": True,
            "confirmation_required": None,
            "read_only": None,
        }
    ]
    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Available tool":
            return next(option for option in options if option.get("provider_id") == "builtin.echo")
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda label, value="", **_kwargs: (
        '{"text": "Hello from Apmatia"}' if label == "Arguments (JSON object)" else value
    )
    mock_streamlit.checkbox.side_effect = lambda _label, value=False, **_kwargs: value
    mock_streamlit.form_submit_button.side_effect = [False, False, True]

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_tool_definitions", return_value=tools
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_agent_tool_assignments", return_value=assignments
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_tools_available_to_agent", return_value=tools
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_tool_definition"
    ) as mock_create, patch(
        "apmatia.interfaces.streamlit.api_client.assign_tool_to_agent"
    ) as mock_assign, patch(
        "apmatia.interfaces.streamlit.api_client.unassign_tool_from_agent"
    ) as mock_unassign, patch(
        "apmatia.interfaces.streamlit.api_client.execute_tool_call",
        return_value={"call_id": "call_123", "status": "success", "result": {"text": "Hello from Apmatia"}, "error": None, "metadata": {"tool_id": 1}},
    ) as mock_execute:
        import apmatia.interfaces.streamlit.pages.tool_management as tool_management_page

        tool_management_page = importlib.reload(tool_management_page)
        tool_management_page.render()

    mock_create.assert_not_called()
    mock_assign.assert_not_called()
    mock_unassign.assert_not_called()
    mock_execute.assert_called_once_with(
        1,
        requester_agent_id=7,
        arguments={"text": "Hello from Apmatia"},
        discussion_id=None,
        approval_granted=False,
    )
    assert mock_streamlit.subheader.call_args_list[0] == call("Agent access")
    mock_streamlit.write.assert_any_call("**Administration tools**")
    mock_streamlit.title.assert_called_with("Tool Management")
    mock_streamlit.caption.assert_any_call(
        "Create tool definitions, grant them to agents, and run safe demo calls through the local API."
    )


def test_tool_management_page_grants_multiple_tools_with_checklists(mock_streamlit):
    """Tool management page can grant several tools at once using checklist controls."""
    agents = [{"id": 7, "name": "Planner"}]
    tools = [
        {
            "id": 0,
            "name": "apmatia_create_agent",
            "description": "Create a new Apmatia agent",
            "provider_id": "builtin.apmatia_create_agent",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        },
        {
            "id": 1,
            "name": "memory_create",
            "description": "Create memory",
            "provider_id": "builtin.memory_create",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        },
        {
            "id": 2,
            "name": "wiki_search",
            "description": "Search wiki",
            "provider_id": "builtin.wiki_search",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        },
        {
            "id": 3,
            "name": "echo",
            "description": "Echo tool",
            "provider_id": "builtin.echo",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        },
    ]
    assignments = []

    def checkbox_side_effect(label, value=False, **_kwargs):
        return label in {
            "memory_create (ID 1, builtin.memory_create)",
            "wiki_search (ID 2, builtin.wiki_search)",
        } or value

    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.checkbox.side_effect = checkbox_side_effect
    mock_streamlit.form_submit_button.side_effect = [True, False, False]

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_tool_definitions", return_value=tools
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_agent_tool_assignments", return_value=assignments
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_tools_available_to_agent", return_value=tools
    ), patch(
        "apmatia.interfaces.streamlit.api_client.assign_tool_to_agent",
        side_effect=[
            {**tools[0], "agent_id": 7, "tool_id": 1},
            {**tools[1], "agent_id": 7, "tool_id": 2},
        ],
    ) as mock_assign, patch(
        "apmatia.interfaces.streamlit.api_client.execute_tool_call"
    ) as mock_execute:
        import apmatia.interfaces.streamlit.pages.tool_management as tool_management_page

        tool_management_page = importlib.reload(tool_management_page)
        tool_management_page.render()

    mock_assign.assert_has_calls(
        [
            call(7, 1, enabled=True, confirmation_required=None, read_only=None),
            call(7, 2, enabled=True, confirmation_required=None, read_only=None),
        ]
    )
    mock_execute.assert_not_called()


def test_tool_management_page_updates_existing_tool(mock_streamlit):
    """Tool management page can edit an existing tool definition without creating a new one."""
    agents = [{"id": 7, "name": "Planner"}]
    tools = [
        {
            "id": 1,
            "name": "echo",
            "description": "Echo tool",
            "provider_id": "builtin.echo",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "metadata": {"builtin": True},
        }
    ]
    mock_streamlit.session_state["tool_editing_id"] = 1
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.checkbox.side_effect = lambda label, value=False, **_kwargs: (False if label == "Enabled" else value)
    mock_streamlit.form_submit_button.side_effect = [False, True, False]

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_tool_definitions", return_value=tools
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_agent_tool_assignments", return_value=[]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_tools_available_to_agent", return_value=[]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.update_tool_definition",
        return_value={**tools[0], "enabled": False},
    ) as mock_update, patch(
        "apmatia.interfaces.streamlit.api_client.create_tool_definition"
    ) as mock_create:
        import apmatia.interfaces.streamlit.pages.tool_management as tool_management_page

        tool_management_page = importlib.reload(tool_management_page)
        tool_management_page.render()

    mock_create.assert_not_called()
    mock_update.assert_called_once_with(
        1,
        name="echo",
        description="Echo tool",
        provider_id="builtin.echo",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        enabled=False,
        confirmation_required=False,
        read_only=True,
        metadata={"builtin": True},
    )
    mock_streamlit.success.assert_any_call("Updated tool definition echo (ID 1).")


def test_memory_management_page_loads_saved_memories(mock_streamlit):
    """Memory management page loads saved memories through the API client."""
    agents = [{"id": 7, "name": "Planner"}]
    memories = [
        {
            "id": 9,
            "title": "Trip note",
            "content": "Bring passport",
            "tags": ["travel"],
            "owner_agent_id": 7,
            "visibility": "draft",
            "status": "active",
            "source_discussion_id": "disc-1",
            "source_message_ids": ["1"],
        }
    ]
    list_memories_calls: list[dict[str, object]] = []
    search_memories_calls: list[tuple[str, dict[str, object]]] = []

    def _selectbox(label, options, index=0, **_kwargs):
        if label == "Agent filter":
            return options[1] if len(options) > 1 else options[0]
        if label == "Select memory":
            return options[index]
        if label == "Owner agent":
            return options[0]
        return options[index]

    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.selectbox.side_effect = _selectbox
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    def _list_memories(**kwargs):
        list_memories_calls.append(kwargs)
        return memories

    def _search_memories(query, **kwargs):
        search_memories_calls.append((query, kwargs))
        return memories

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_memories", side_effect=_list_memories
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_memory", return_value=memories[0]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.search_memories", side_effect=_search_memories
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_memory"
    ) as mock_create, patch(
        "apmatia.interfaces.streamlit.api_client.update_memory"
    ) as mock_update, patch(
        "apmatia.interfaces.streamlit.api_client.archive_memory"
    ) as mock_archive, patch(
        "apmatia.interfaces.streamlit.api_client.delete_memory"
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.memory_management as memory_management_page

        memory_management_page = importlib.reload(memory_management_page)
        memory_management_page.render()

    mock_create.assert_not_called()
    mock_update.assert_not_called()
    mock_archive.assert_not_called()
    mock_delete.assert_not_called()
    mock_streamlit.title.assert_called_with("Memory Management")
    mock_streamlit.caption.assert_any_call(
        "Browse memories by agent, user, or group, grouped by owning agent."
    )
    assert list_memories_calls == [{"include_archived": True, "owner_agent_id": 7}]
    assert search_memories_calls == []


def test_memory_management_page_limits_owner_agent_choices_to_writable_agents(mock_streamlit):
    """The create form should only offer agents owned by the current user."""
    agents = [
        {"id": 7, "name": "Planner", "owner_user_id": 1, "owner_group_id": None},
        {"id": 8, "name": "Foreign", "owner_user_id": 2, "owner_group_id": None},
    ]
    memories = []
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 1}
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    def _selectbox(label, options, index=0, **_kwargs):
        if label == "Agent filter":
            return options[0]
        if label == "Select memory":
            return options[index] if options else None
        if label == "Owner agent":
            assert options == [None, 7]
            return options[1]
        return options[index]

    mock_streamlit.selectbox.side_effect = _selectbox

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_memories", return_value=memories
    ), patch(
        "apmatia.interfaces.streamlit.api_client.search_memories", return_value=memories
    ):
        import apmatia.interfaces.streamlit.pages.memory_management as memory_management_page

        memory_management_page = importlib.reload(memory_management_page)
        memory_management_page.render()

    mock_streamlit.info.assert_any_call("No memories found.")


def test_model_management_page_shows_saved_model_url(mock_streamlit):
    """Existing model cards show the saved base URL for verification."""
    configs = [
        {
            "id": 1,
            "user_alias": "Local Model",
            "backend": "openai_compatible",
            "provider_name": "Qwen",
            "model_url": "http://localhost:5001",
            "api_key": "",
            "max_response_size": 8192,
            "system_prompt": "",
            "metadata": {},
        }
    ]
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]

    with patch("apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=configs):
        import apmatia.interfaces.streamlit.pages.model_management as model_management_page

        model_management_page = importlib.reload(model_management_page)
        model_management_page.render()

    mock_streamlit.caption.assert_any_call("URL: http://localhost:5001")


def test_model_management_page_can_test_ai_model(mock_streamlit):
    """Model management can probe a saved AI model through the API."""
    configs = [
        {
            "id": 1,
            "user_alias": "Local Model",
            "backend": "openai_compatible",
            "provider_name": "Qwen",
            "model_url": "http://localhost:5001",
            "api_key": "",
            "max_response_size": 8192,
            "system_prompt": "",
            "metadata": {},
        }
    ]
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.number_input.side_effect = lambda _label, value=0, **_kwargs: value
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.button.side_effect = lambda label, *args, **_kwargs: label == "Test"

    with patch("apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=configs), patch(
        "apmatia.interfaces.streamlit.api_client.test_llm_config",
        return_value={"reply_preview": "ready and connected"},
    ) as mock_test:
        import apmatia.interfaces.streamlit.pages.model_management as model_management_page

        model_management_page = importlib.reload(model_management_page)
        model_management_page.render()

    mock_test.assert_called_once_with(1)
    mock_streamlit.success.assert_any_call(
        "AI model responded: ready and connected"
    )


def test_model_management_page_uses_ai_model_labels(mock_streamlit):
    """Model management page uses the updated AI model terminology and fields."""
    llm_configs = [
        {"id": 301, "user_alias": "Default", "provider_name": "gpt-4o-mini"},
        {"id": 302, "user_alias": "Active", "provider_name": "gpt-4o"},
    ]
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.form_submit_button.return_value = False

    with patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch("apmatia.interfaces.streamlit.api_client.create_llm_config") as mock_create, patch(
        "apmatia.interfaces.streamlit.api_client.update_llm_config"
    ) as mock_update, patch(
        "apmatia.interfaces.streamlit.api_client.delete_llm_config"
    ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.model_management as model_management_page

        model_management_page = importlib.reload(model_management_page)
        model_management_page.render()

    mock_create.assert_not_called()
    mock_update.assert_not_called()
    mock_delete.assert_not_called()
    mock_streamlit.title.assert_called_with("Model Management")
    mock_streamlit.caption.assert_any_call(
        "Create, edit, and remove AI model objects through the local API."
    )
    mock_streamlit.subheader.assert_any_call("AI Model")
    mock_streamlit.subheader.assert_any_call("Existing AI models")


def test_user_management_page_loads_and_manages_groups(mock_streamlit):
    """User management uses the API client for users, groups, and membership updates."""
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 1, "username": "nick"}
    mock_streamlit.session_state["user_management_selected_group_id"] = 10
    mock_streamlit.form_submit_button.side_effect = [True, False, False, False]
    mock_streamlit.text_input.side_effect = ["newuser", "newpass", "nick", "", "team"]
    mock_streamlit.text_area.return_value = "Team description"
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.button.return_value = False

    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "User" and len(options) > 1:
            return options[1]
        if label == "Role":
            return "member"
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect

    users = [
        {"id": 1, "username": "nick", "is_enabled": True},
        {"id": 2, "username": "alice", "is_enabled": False},
    ]
    groups = [
        {"id": 10, "name": "team", "description": "Team description", "created_by_user_id": 1},
        {"id": 11, "name": "other", "description": "", "created_by_user_id": 2},
    ]
    memberships = [
        {"id": 100, "group_id": 10, "user_id": 1, "role": "owner", "is_enabled": True},
        {"id": 101, "group_id": 10, "user_id": 2, "role": "member", "is_enabled": True},
    ]

    with patch("apmatia.interfaces.streamlit.api_client.list_users", return_value=users), patch(
        "apmatia.interfaces.streamlit.api_client.list_groups", return_value=groups
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_user"
    ) as mock_create_user, patch(
        "apmatia.interfaces.streamlit.api_client.update_user"
    ) as mock_update_user, patch(
        "apmatia.interfaces.streamlit.api_client.delete_user"
    ) as mock_delete_user, patch(
        "apmatia.interfaces.streamlit.api_client.create_group"
    ) as mock_create_group, patch(
        "apmatia.interfaces.streamlit.api_client.update_group"
    ) as mock_update_group, patch(
        "apmatia.interfaces.streamlit.api_client.delete_group"
    ) as mock_delete_group, patch(
        "apmatia.interfaces.streamlit.api_client.list_group_members",
        return_value=memberships,
    ) as mock_list_group_members, patch(
        "apmatia.interfaces.streamlit.api_client.add_group_member"
    ) as mock_add_group_member, patch(
        "apmatia.interfaces.streamlit.api_client.set_group_membership_enabled"
    ) as mock_set_membership_enabled:
        import apmatia.interfaces.streamlit.pages.user_management as user_management_page

        user_management_page = importlib.reload(user_management_page)
        user_management_page.render()

    mock_create_user.assert_called_once_with(username="newuser", password="newpass")
    mock_update_user.assert_not_called()
    mock_delete_user.assert_not_called()
    mock_create_group.assert_not_called()
    mock_update_group.assert_not_called()
    mock_delete_group.assert_not_called()
    mock_list_group_members.assert_called_once_with(10)
    mock_add_group_member.assert_not_called()
    mock_set_membership_enabled.assert_not_called()
    mock_streamlit.title.assert_called_with("User Management")
    mock_streamlit.caption.assert_any_call(
        "Create users, edit your account, and manage the groups you own through the local API."
    )


def test_discussion_page_uses_agent_and_discussion_backend(mock_streamlit):
    """Discussion page selects agents by ID and sends prompts through the API."""
    agents = [
        {"id": 7, "name": "Planner", "active_model_id": 301},
        {"id": 8, "name": "Writer"},
    ]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [
            {"discussion_id": "IDabc123", "title": "Sprint Planning", "participant_agent_ids": [7]},
            {"discussion_id": "IDdef456", "title": "Research", "participant_agent_ids": [7]},
        ],
    }
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [{"role": "User", "text": "Hello"}],
        "last_error": None,
    }
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.text_area.return_value = "Write a status update."
    mock_streamlit.form_submit_button.return_value = True
    mock_streamlit.button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.prompt_discussion"
    ) as mock_prompt:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()

    mock_prompt.assert_called_once()
    payload = mock_prompt.call_args.kwargs
    assert payload["agent_id"] == 7
    assert payload["prompt"] == "Write a status update."
    assert payload["attachments"] == []
    mock_streamlit.title.assert_called_with("Discussion")
    mock_streamlit.caption.assert_any_call(
        "Using Default via openai_compatible at http://localhost:5001."
    )
    mock_streamlit.markdown.assert_any_call("Hello")


def test_discussion_page_can_update_participants(mock_streamlit):
    """The discussion page lets you assign multiple agents to the current discussion."""
    agents = [
        {"id": 7, "name": "Planner", "active_model_id": 301},
        {"id": 8, "name": "Writer", "active_model_id": 302},
    ]
    llm_configs = [
        {"id": 301, "user_alias": "Planner Model", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
        {"id": 302, "user_alias": "Writer Model", "backend": "openai_compatible", "model_url": "http://localhost:6001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [
            {
                "discussion_id": "IDabc123",
                "title": "Shared Thread",
                "participant_agent_ids": [7],
                "chat_mode": "round_robin",
            }
        ],
    }
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [],
        "last_error": None,
        "is_streaming": False,
        "chat_mode": "round_robin",
        "chat_pause_seconds": None,
        "chat_is_paused": False,
        "chat_turn_index": 0,
        "chat_coordinator_agent_id": None,
    }
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.multiselect.return_value = [7, 8]
    mock_streamlit.button.side_effect = lambda label, *args, **kwargs: label == "Save chat targets"
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.update_discussion"
    ) as mock_update:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()

    mock_update.assert_called_once_with("IDabc123", participant_agent_ids=[7, 8])


def test_message_text_blocks_preserve_markdown_and_emoji(mock_streamlit):
    import apmatia.interfaces.streamlit.components.message_card as message_card

    importlib.reload(message_card)
    message_card.render_message_text_block("Hello **world**\nLine two 😀")

    mock_streamlit.markdown.assert_called_once_with("Hello **world**\nLine two 😀")


def test_discussion_message_titles_use_user_and_agent_names(mock_streamlit):
    """Message cards show the authenticated username and selected agent name."""
    import apmatia.interfaces.streamlit.components.message_card as message_card
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    importlib.reload(message_card)
    discussion_page = importlib.reload(discussion_page)
    discussion_page._render_message_card(
        "IDabc123",
        0,
        {"role": "User", "text": "Hello"},
        username="nick",
        agent_name="Planner",
    )
    discussion_page._render_message_card(
        "IDabc123",
        1,
        {"role": "Assistant", "text": "Hi"},
        username="nick",
        agent_name="Planner",
    )

    mock_streamlit.caption.assert_any_call("nick")
    mock_streamlit.caption.assert_any_call("Planner")


def test_tutor_page_loads_discussion_and_wiki_workspace(mock_streamlit):
    agents = [{"id": 7, "name": "Tutor", "active_model_id": 301}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDtutor01",
        "discussions": [
            {
                "discussion_id": "IDregular01",
                "title": "Regular discussion",
                "participant_agent_ids": [7],
                "focused_wiki_id": None,
            },
            {
                "discussion_id": "IDtutor01",
                "title": "Algebra session",
                "participant_agent_ids": [7],
                "focused_wiki_id": "wiki_algebra",
            }
        ],
    }
    snapshot = {
        "discussion_id": "IDtutor01",
        "messages": [{"role": "User", "text": "Can we solve for x?"}],
        "last_error": None,
        "is_streaming": False,
    }
    wikis = [{"id": "wiki_algebra", "title": "Algebra I", "description": "Session notes"}]
    wiki_tree = {
        "wiki": {
            "id": "wiki_algebra",
            "title": "Algebra I",
            "description": "Session notes",
            "root_node_id": "wn_root",
        },
        "root": {
            "id": "wn_root",
            "wiki_id": "wiki_algebra",
            "parent_id": None,
            "node_type": "branch",
            "title": "Algebra I",
            "body": "",
            "sort_order": 0,
            "children": [
                {
                    "id": "wn_leaf",
                    "wiki_id": "wiki_algebra",
                    "parent_id": "wn_root",
                    "node_type": "leaf",
                    "title": "Linear equations",
                    "body": "Balance both sides.",
                    "sort_order": 0,
                    "children": [],
                }
            ],
        },
    }
    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_wikis",
        return_value=wikis,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_wiki_tree",
        return_value=wiki_tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.search_wiki",
        return_value=[],
    ):
        import apmatia.interfaces.streamlit.pages.tutor as tutor_page

        tutor_page = importlib.reload(tutor_page)
        tutor_page.render()

    mock_streamlit.title.assert_called_with("Tutor")
    mock_streamlit.caption.assert_any_call("Building notes in: Algebra I")
    mock_streamlit.caption.assert_any_call("Selected node: Algebra I")


def test_tutor_page_hides_regular_discussions_from_saved_session_picker(mock_streamlit):
    agents = [{"id": 7, "name": "Tutor", "active_model_id": 301}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDregular01",
        "discussions": [
            {
                "discussion_id": "IDregular01",
                "title": "Regular discussion",
                "participant_agent_ids": [7],
                "focused_wiki_id": None,
            },
            {
                "discussion_id": "IDtutor01",
                "title": "Saved tutor session",
                "participant_agent_ids": [7],
                "focused_wiki_id": "wiki_algebra",
            },
        ],
    }
    snapshot = {
        "discussion_id": "IDtutor01",
        "messages": [],
        "last_error": None,
        "is_streaming": False,
    }
    wikis = [{"id": "wiki_algebra", "title": "Algebra I", "description": "Session notes"}]
    wiki_tree = {
        "wiki": {
            "id": "wiki_algebra",
            "title": "Algebra I",
            "description": "Session notes",
            "root_node_id": "wn_root",
        },
        "root": {
            "id": "wn_root",
            "wiki_id": "wiki_algebra",
            "parent_id": None,
            "node_type": "branch",
            "title": "Algebra I",
            "body": "",
            "sort_order": 0,
            "children": [],
        },
    }

    def _selectbox(label, options, index=0, **_kwargs):
        if label == "Discussion":
            assert [option.get("title") for option in options] == ["Saved tutor session"]
        return options[index]

    mock_streamlit.selectbox.side_effect = _selectbox
    mock_streamlit.text_input.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.text_area.side_effect = lambda _label, value="", **_kwargs: value
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_wikis",
        return_value=wikis,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_wiki_tree",
        return_value=wiki_tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.search_wiki",
        return_value=[],
    ), patch(
        "apmatia.interfaces.streamlit.api_client.open_discussion"
    ) as mock_open:
        import apmatia.interfaces.streamlit.pages.tutor as tutor_page

        tutor_page = importlib.reload(tutor_page)
        tutor_page.render()

    mock_open.assert_called_once_with("IDtutor01")


def test_tutor_page_creates_wiki_without_session_state_error(mock_streamlit):
    agents = [{"id": 7, "name": "Tutor", "active_model_id": 301}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {"current_discussion_id": None, "discussions": []}
    wikis = []
    snapshot = {"discussion_id": None, "messages": [], "last_error": None, "is_streaming": False}
    wiki_tree = None

    def _selectbox(label, options, index=0, **_kwargs):
        return options[index]

    mock_streamlit.selectbox.side_effect = _selectbox
    mock_streamlit.text_input.side_effect = lambda label, value="", **_kwargs: "Algebra Notes" if label == "Wiki title" else value
    mock_streamlit.text_area.side_effect = lambda label, value="", **_kwargs: "Notes" if label == "Wiki description" else value
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree", return_value=tree
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state", return_value=snapshot
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_wikis", return_value=wikis
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_wiki_tree", return_value=wiki_tree
    ), patch(
        "apmatia.interfaces.streamlit.api_client.search_wiki", return_value=[]
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_wiki",
        return_value={"wiki": {"id": "wiki_123", "title": "Algebra Notes", "description": "Notes"}},
    ) as mock_create:
        import apmatia.interfaces.streamlit.pages.tutor as tutor_page

        tutor_page = importlib.reload(tutor_page)
        tutor_page.render()

    mock_create.assert_not_called()
    assert mock_streamlit.session_state["tutor_clear_new_wiki_fields"] is False


def test_tutor_live_discussion_uses_selected_tutor_agent(mock_streamlit):
    agents = [
        {"id": 9, "name": "Other Agent", "active_model_id": 301},
        {"id": 7, "name": "Tutor Agent", "active_model_id": 302},
    ]
    snapshot = {"discussion_id": "disc-1", "messages": [], "last_error": None, "is_streaming": False}
    wiki_tree = {
        "wiki": {
            "id": "wiki-1",
            "title": "Tutor Wiki",
            "description": "Notes",
            "root_node_id": "root-1",
        },
        "root": {
            "id": "root-1",
            "wiki_id": "wiki-1",
            "parent_id": None,
            "node_type": "branch",
            "title": "Tutor Wiki",
            "body": "",
            "sort_order": 0,
            "children": [],
        },
    }
    mock_streamlit.session_state["tutor_selected_agent_id"] = 7
    mock_streamlit.session_state["tutor_selected_wiki_id"] = "wiki-1"
    mock_streamlit.text_area.return_value = "Ask the tutor"
    mock_streamlit.form_submit_button.return_value = True
    mock_streamlit.button.side_effect = lambda *args, **kwargs: False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_wiki_tree",
        return_value=wiki_tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.prompt_discussion",
    ) as mock_prompt:
        import apmatia.interfaces.streamlit.pages.tutor_live_discussion as live_page

        live_page = importlib.reload(live_page)
        live_page.render()

    mock_prompt.assert_called_once()
    assert mock_prompt.call_args.kwargs["agent_id"] == 7


def test_discussion_selectbox_auto_opens_selected_discussion(mock_streamlit):
    """Changing the discussion dropdown opens that discussion without a button."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [
            {"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]},
            {"discussion_id": "IDdef456", "title": "Next", "participant_agent_ids": [7]},
        ],
    }
    snapshot = {"discussion_id": "IDabc123", "messages": [], "last_error": None}
    mock_streamlit.selectbox.side_effect = lambda label, options, index=0, **_kwargs: (
        options[0] if label == "Agent" else options[1]
    )
    mock_streamlit.button.return_value = False
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.open_discussion"
    ) as mock_open:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()

    mock_open.assert_called_once_with("IDdef456")
    mock_streamlit.rerun.assert_called()


def test_discussion_page_filters_discussions_by_selected_agent(mock_streamlit):
    """The discussion dropdown only shows discussions associated with the selected agent."""
    agents = [{"id": 7, "name": "Planner"}, {"id": 8, "name": "Researcher"}]
    llm_configs = [
        {"id": 301, "user_alias": "Planner Model", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
        {"id": 302, "user_alias": "Research Model", "backend": "openai_compatible", "model_url": "http://localhost:6001"},
    ]
    tree = {
        "current_discussion_id": "IDghi789",
        "discussions": [
            {"discussion_id": "IDabc123", "title": "Planner Thread", "participant_agent_ids": [7]},
            {"discussion_id": "IDdef456", "title": "Shared Thread", "participant_agent_ids": [7, 8]},
            {"discussion_id": "IDghi789", "title": "Research Thread", "participant_agent_ids": [8]},
        ],
    }
    snapshot = {"discussion_id": "IDghi789", "messages": [], "last_error": None, "is_streaming": False}
    captured_discussion_options = []

    def _selectbox(label, options, index=0, **_kwargs):
        if label == "Discussion":
            captured_discussion_options.extend(options)
            return options[0]
        return options[1]

    mock_streamlit.selectbox.side_effect = _selectbox
    mock_streamlit.button.return_value = False
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.open_discussion"
    ) as mock_open:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()

    assert [option["discussion_id"] for option in captured_discussion_options] == ["IDabc123", "IDdef456"]
    mock_open.assert_called_once_with("IDabc123")


def test_discussion_delete_selected_button_calls_api(mock_streamlit):
    """Delete selected discussion moves the selected discussion to trash."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [{"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]}],
    }
    snapshot = {"discussion_id": "IDabc123", "messages": [], "last_error": None}
    render_phase = {"value": 0}

    def button_side_effect(label, *args, **_kwargs):
        if render_phase["value"] == 0:
            return label == "Delete selected discussion"
        return label == "Delete"

    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.button.side_effect = button_side_effect
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
        ), patch(
            "apmatia.interfaces.streamlit.api_client.delete_discussion"
        ) as mock_delete:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()
        render_phase["value"] = 1
        discussion_page.render()

    mock_delete.assert_called_once_with("IDabc123")
    mock_streamlit.success.assert_called_with("Discussion moved to trash.")
    mock_streamlit.rerun.assert_called()


def test_discussion_delete_last_discussion_does_not_open_replacement(mock_streamlit):
    """Deleting the final visible discussion does not auto-open or auto-create a new one."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [{"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]}],
    }
    snapshot = {"discussion_id": "IDabc123", "messages": [], "last_error": None, "is_streaming": False}
    render_phase = {"value": 0}

    def button_side_effect(label, *args, **_kwargs):
        if render_phase["value"] == 0:
            return label == "Delete selected discussion"
        return label == "Delete"

    mock_streamlit.selectbox.side_effect = lambda _label, options, index=0, **_kwargs: options[index]
    mock_streamlit.button.side_effect = button_side_effect
    mock_streamlit.form_submit_button.return_value = False

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.delete_discussion",
        return_value={"status": "deleted", "result": {"discussion_id": "IDabc123", "next_discussion_id": None}},
    ) as mock_delete, patch(
        "apmatia.interfaces.streamlit.api_client.open_discussion"
        ) as mock_open:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.render()
        render_phase["value"] = 1
        discussion_page.render()

    mock_delete.assert_called_once_with("IDabc123")
    mock_open.assert_not_called()


def test_contacts_shell_reuses_existing_discussion_after_refresh(mock_streamlit):
    """Refreshing the contacts shell should reopen the existing discussion instead of creating a duplicate."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    contact = {"contact_id": "agent:7", "contact_type": "agent", "label": "Planner"}
    tree = {
        "discussions": [
            {
                "discussion_id": "IDabc123",
                "title": "Planner",
                "participant_agent_ids": [7],
            }
        ]
    }

    with patch.object(streamlit_app, "discussion_tree", return_value=tree), patch.object(
        streamlit_app, "open_discussion"
    ) as mock_open, patch.object(streamlit_app, "create_discussion") as mock_create:
        streamlit_app._activate_contacts_contact(contact)

    assert mock_streamlit.session_state["contacts_shell_active"] is True
    assert mock_streamlit.session_state["contacts_active_discussion_id"] == "IDabc123"
    assert mock_streamlit.session_state["contacts_contact_discussion_ids"]["agent:7"] == "IDabc123"
    mock_open.assert_called_once_with("IDabc123")
    mock_create.assert_not_called()


def test_discussion_message_copy_action_renders_html_button(mock_streamlit):
    """The message copy action renders a browser-side copy button."""

    import apmatia.interfaces.streamlit.components.message_card as message_card
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    importlib.reload(message_card)
    discussion_page = importlib.reload(discussion_page)
    discussion_page._render_message_card(
        "IDabc123",
        0,
        {"role": "User", "text": "Hello"},
        username="nick",
        agent_name="Planner",
    )

    html_calls = [call.args[0] for call in mock_streamlit.html.call_args_list]
    assert any("apmatia-copy-button" in body for body in html_calls)
    assert any("apmatia-copy-glyph" in body for body in html_calls)
    assert any("data-copy=\"SGVsbG8=\"" in body for body in html_calls)
    assert any("navigator.clipboard.writeText(text)" in body for body in html_calls)
    mock_streamlit.rerun.assert_not_called()


def test_clipboard_button_component_renders_main_dom_copy_control(mock_streamlit):
    """The reusable clipboard component writes directly to the browser clipboard."""
    import apmatia.interfaces.streamlit.components.clipboard_button as clipboard_button

    clipboard_button = importlib.reload(clipboard_button)
    clipboard_button.render_clipboard_button("Hello", "copy-hello", aria_label="Copy message")

    rendered_html = "\n".join(call.args[0] for call in mock_streamlit.html.call_args_list)
    assert "apmatia-copy-button" in rendered_html
    assert "apmatia-copy-glyph" in rendered_html
    assert 'aria-label="Copy message"' in rendered_html
    assert 'data-copy="SGVsbG8="' in rendered_html
    assert "navigator.clipboard.writeText(text)" in rendered_html


def test_clipboard_image_paste_bridge_renders_paste_listener(mock_streamlit):
    """The paste bridge listens for clipboard images without blocking text paste."""
    import apmatia.interfaces.streamlit.components.clipboard_button as clipboard_button

    clipboard_button = importlib.reload(clipboard_button)
    clipboard_button.render_clipboard_image_paste_bridge("discussion-attachments")

    rendered_html = "\n".join(call.args[0] for call in mock_streamlit.html.call_args_list)
    assert "addEventListener(\"paste\", handler, true)" in rendered_html
    assert "DataTransfer" in rendered_html
    assert "input.files = dataTransfer.files" in rendered_html
    assert "clipboardData" in rendered_html
    assert "pasted-screenshot" in rendered_html


def test_message_card_css_hides_streamlit_code_copy_button(mock_streamlit):
    """Only Apmatia's footer copy control is shown on message cards."""
    import apmatia.interfaces.streamlit.components.message_card as message_card

    message_card = importlib.reload(message_card)
    message_card.apply_message_card_css()

    rendered_css = "\n".join(call.args[0] for call in mock_streamlit.html.call_args_list)
    assert '[data-testid="stCodeCopyButton"]' in rendered_css
    assert '[data-testid="stCodeBlock"] button' in rendered_css
    assert "display: none !important" in rendered_css
    assert "apm-message-footer" in rendered_css
    assert "stMarkdownContainer" in rendered_css
    assert "Apple Color Emoji" in rendered_css


def test_render_message_text_block_uses_markdown(mock_streamlit):
    """Message text rendering preserves markdown formatting and emoji."""
    import apmatia.interfaces.streamlit.components.message_card as message_card

    message_card = importlib.reload(message_card)
    message_card.render_message_text_block("Hello <Nick>\nWorld 😀")

    mock_streamlit.markdown.assert_called_once_with("Hello <Nick>\nWorld 😀")


def test_message_card_css_includes_emoji_safe_font_stack(mock_streamlit):
    import apmatia.interfaces.streamlit.components.message_card as message_card

    message_card = importlib.reload(message_card)
    message_card.apply_message_card_css()

    rendered_css = "\n".join(call.args[0] for call in mock_streamlit.html.call_args_list)
    assert "Apple Color Emoji" in rendered_css
    assert "Segoe UI Emoji" in rendered_css
    assert "Noto Color Emoji" in rendered_css


def test_discussion_message_edit_action_sets_target_and_reruns(mock_streamlit):
    """The message edit action opens inline editing on the first click."""
    mock_streamlit.button.side_effect = lambda _label, *args, **kwargs: kwargs.get("help") == "Edit"

    import apmatia.interfaces.streamlit.components.message_card as message_card
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    importlib.reload(message_card)
    discussion_page = importlib.reload(discussion_page)
    discussion_page._render_message_card(
        "IDabc123",
        0,
        {"role": "User", "text": "Hello"},
        username="nick",
        agent_name="Planner",
    )

    assert mock_streamlit.session_state["discussion_edit_target"] == {
        "discussion_id": "IDabc123",
        "index": 0,
        "text": "Hello",
    }
    mock_streamlit.rerun.assert_called_once()


def test_discussion_message_delete_action_sets_target_and_reruns(mock_streamlit):
    """The message delete action opens confirmation on the first click."""
    mock_streamlit.button.side_effect = lambda _label, *args, **kwargs: kwargs.get("help") == "Delete"

    import apmatia.interfaces.streamlit.components.message_card as message_card
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    importlib.reload(message_card)
    discussion_page = importlib.reload(discussion_page)
    discussion_page._render_message_card(
        "IDabc123",
        0,
        {"role": "User", "text": "Hello"},
        username="nick",
        agent_name="Planner",
    )

    assert mock_streamlit.session_state["discussion_delete_target"] == {
        "discussion_id": "IDabc123",
        "index": 0,
        "text": "Hello",
    }
    mock_streamlit.rerun.assert_called_once()


def test_discussion_activity_status_text_includes_generation_and_server_details(mock_streamlit):
    """The live status subtitle should describe the agent and llama.cpp stats once."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)

    activity = {
        "stage": "generating",
        "agent_name": "Planner",
        "speaker_name": "Planner",
    }
    llama_status = {
        "chat_format": "peg-native",
        "thinking_enabled": True,
        "selected_slot_id": 0,
        "current_task_id": 220,
        "prompt_processing_progress": 0.995794,
        "prompt_processing_n_tokens": 947,
        "prompt_tokens_total": 951,
        "prompt_eval": {"tokens_per_second": 203.64},
        "eval": {"tokens_per_second": 22.6},
        "total_time_ms": 31612.67,
        "total_tokens": 1559,
        "slots_idle": False,
    }

    text = discussion_page._activity_status_text(
        activity,
        agent_lookup={},
        model_lookup={},
        llama_server_status=llama_status,
    )

    assert text is not None
    assert "Planner is generating a response." in text
    assert text.count("generating a response") == 1
    assert "slot 0 task 220" in text
    assert "processing prompt" in text
    assert "99.6%" in text
    assert "prompt 203.64 tok/s" in text
    assert "generation 22.60 tok/s" in text
    assert "total 1559 tokens / 31.61s" in text


def test_discussion_message_card_renders_llama_stats_caption(mock_streamlit):
    """Assistant responses should show persisted llama.cpp stats beneath the message."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)
    message = {
        "role": "Assistant",
        "text": "Here is the answer.",
        "speaker_name": "Planner",
        "metadata": {
            "llama_server_status": {
                "chat_format": "peg-native",
                "thinking_enabled": True,
                "selected_slot_id": 0,
                "current_task_id": 220,
                "prompt_processing_progress": 0.995794,
                "prompt_processing_n_tokens": 947,
                "prompt_tokens_total": 951,
                "prompt_eval": {"tokens_per_second": 203.64},
                "eval": {"tokens_per_second": 22.6},
                "total_time_ms": 31612.67,
                "total_tokens": 1559,
                "slots_idle": False,
            }
        },
    }

    discussion_page._render_message_card(
        "IDabc123",
        1,
        message,
        username="nick",
        agent_name="Planner",
        activity=None,
        llama_server_status=None,
    )

    captions = [call.args[0] for call in mock_streamlit.caption.call_args_list]
    assert any("processing prompt" in caption for caption in captions)
    assert any("generation 22.60 tok/s" in caption for caption in captions)


def test_discussion_message_card_ignores_unrelated_live_status(mock_streamlit):
    """A finished message should keep its own stats when another agent is currently active."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)
    message = {
        "role": "Assistant",
        "text": "Here is the answer.",
        "speaker_name": "Planner",
        "metadata": {
            "llama_server_status": {
                "chat_format": "peg-native",
                "thinking_enabled": True,
                "selected_slot_id": 0,
                "current_task_id": 220,
                "prompt_processing_progress": 0.995794,
                "prompt_processing_n_tokens": 947,
                "prompt_tokens_total": 951,
                "prompt_eval": {"tokens_per_second": 203.64},
                "eval": {"tokens_per_second": 22.6},
                "total_time_ms": 31612.67,
                "total_tokens": 1559,
                "slots_idle": False,
            }
        },
    }
    live_status = {
        "chat_format": "peg-native",
        "thinking_enabled": False,
        "selected_slot_id": 1,
        "current_task_id": 999,
        "prompt_processing_progress": 0.25,
        "prompt_processing_n_tokens": 128,
        "prompt_tokens_total": 512,
        "prompt_eval": {"tokens_per_second": 44.0},
        "eval": {"tokens_per_second": 8.5},
        "total_time_ms": 2400.0,
        "total_tokens": 256,
        "slots_idle": False,
    }

    discussion_page._render_message_card(
        "IDabc123",
        1,
        message,
        username="nick",
        agent_name="Planner",
        activity={
            "stage": "generating",
            "agent_name": "Nova-Wiki-Tutor",
            "speaker_name": "Nova-Wiki-Tutor",
        },
        llama_server_status=live_status,
    )

    captions = [call.args[0] for call in mock_streamlit.caption.call_args_list]
    assert any("generation 22.60 tok/s" in caption for caption in captions)
    assert any("total 1559 tokens / 31.61s" in caption for caption in captions)
    assert not any("generation 8.50 tok/s" in caption for caption in captions)
    assert not any("slot 1 task 999" in caption for caption in captions)


def test_discussion_activity_status_text_includes_tool_details(mock_streamlit):
    """Tool activity should say which agent is executing the tool and with what parameters."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)

    activity = {
        "stage": "tool",
        "agent_name": "Planner",
        "speaker_name": "Planner",
        "tool": {
            "name": "wiki_lookup",
            "status": "running",
            "arguments": {"query": "llama.cpp"},
        },
    }

    text = discussion_page._activity_status_text(
        activity,
        agent_lookup={},
        model_lookup={},
        llama_server_status=None,
    )

    assert text is not None
    assert "Planner is executing wiki_lookup (running)." in text
    assert 'Parameters: {"query": "llama.cpp"}.' in text


def test_discussion_render_messages_places_live_activity_in_placeholder_card(mock_streamlit):
    """A new active turn should render as its own live card instead of rewriting the previous message."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [
            {"role": "User", "text": "Hello"},
            {
                "role": "Assistant",
                "text": "All done.",
                "speaker_name": "Planner",
                "metadata": {
                    "llama_server_status": {
                        "chat_format": "peg-native",
                        "thinking_enabled": True,
                        "selected_slot_id": 0,
                        "current_task_id": 220,
                        "prompt_processing_progress": 1.0,
                        "prompt_processing_n_tokens": 947,
                        "prompt_tokens_total": 951,
                        "prompt_eval": {"tokens_per_second": 203.64},
                        "eval": {"tokens_per_second": 22.6},
                        "total_time_ms": 31612.67,
                        "total_tokens": 1559,
                        "slots_idle": False,
                    }
                },
            },
        ],
        "last_error": None,
        "is_streaming": True,
        "activity": {
            "stage": "generating",
            "agent_name": "Nova-Wiki-Tutor",
            "speaker_name": "Nova-Wiki-Tutor",
        },
        "llama_server_status": {
            "chat_format": "peg-native",
            "thinking_enabled": False,
            "selected_slot_id": 1,
            "current_task_id": 999,
            "prompt_processing_progress": 0.25,
            "prompt_processing_n_tokens": 128,
            "prompt_tokens_total": 512,
            "prompt_eval": {"tokens_per_second": 44.0},
            "eval": {"tokens_per_second": 8.5},
            "total_time_ms": 2400.0,
            "total_tokens": 256,
            "slots_idle": False,
        },
    }
    rendered = []

    def fake_render_message_card(*args, **kwargs):
        rendered.append({"args": args, "kwargs": kwargs})

    with patch.object(discussion_page, "render_message_card", side_effect=fake_render_message_card):
        discussion_page._render_messages(
            snapshot,
            username="nick",
            agent_name="Planner",
        )

    assert len(rendered) == 3
    assert rendered[1]["kwargs"]["card_key"] == "discussion-IDabc123-1"
    assert rendered[1]["kwargs"]["details"] is None
    assert rendered[2]["kwargs"]["card_key"] == "discussion-IDabc123-live-activity"
    assert rendered[2]["kwargs"]["subtitle"] is None


def test_discussion_page_shows_stop_button_while_streaming(mock_streamlit):
    """The discussion submit control becomes a stop button during streaming."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [{"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]}],
    }
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [{"role": "User", "text": "Hello"}],
        "last_error": None,
        "is_streaming": True,
    }
    mock_streamlit.selectbox.return_value = agents[0]
    mock_streamlit.text_area.return_value = "Write a status update."
    mock_streamlit.button.side_effect = lambda label, *args, **kwargs: label == "Stop"

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.stop_discussion"
    ) as mock_stop:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
        discussion_page.stop_discussion = mock_stop
        discussion_page.render()

    mock_stop.assert_called_once()
    mock_streamlit.button.assert_any_call("Stop", use_container_width=False)
    mock_streamlit.success.assert_called_with("Message stopped. Refreshing discussion.")


def test_discussion_page_returns_to_send_message_when_streaming_finishes(mock_streamlit):
    """The discussion submit control returns to send mode after a refresh shows streaming is done."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [{"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]}],
    }
    streaming_snapshot = {
        "discussion_id": "IDabc123",
        "messages": [{"role": "User", "text": "Hello"}],
        "last_error": None,
        "is_streaming": True,
    }
    finished_snapshot = {
        "discussion_id": "IDabc123",
        "messages": [{"role": "User", "text": "Hello"}],
        "last_error": None,
        "is_streaming": False,
    }
    mock_streamlit.selectbox.return_value = agents[0]
    mock_streamlit.button.return_value = False
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.fragment.__module__ = "streamlit.testing"
    mock_streamlit.fragment.side_effect = lambda run_every=0.5: (lambda func: func)

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        side_effect=[streaming_snapshot, finished_snapshot],
    ), patch(
        "apmatia.interfaces.streamlit.api_client.stop_discussion"
    ) as mock_stop:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
    discussion_page.render()

    mock_stop.assert_not_called()
    assert mock_streamlit.rerun.call_count >= 1


def test_discussion_page_keeps_stop_mode_while_streaming(mock_streamlit):
    """Streaming keeps the discussion page on the stop control until the backend finishes."""
    agents = [{"id": 7, "name": "Planner"}]
    llm_configs = [
        {"id": 301, "user_alias": "Default", "backend": "openai_compatible", "model_url": "http://localhost:5001"},
    ]
    tree = {
        "current_discussion_id": "IDabc123",
        "discussions": [{"discussion_id": "IDabc123", "title": "Current", "participant_agent_ids": [7]}],
    }
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [{"role": "User", "text": "Hello"}],
        "last_error": None,
        "is_streaming": True,
    }
    mock_streamlit.selectbox.return_value = agents[0]
    mock_streamlit.form_submit_button.return_value = False
    mock_streamlit.button.side_effect = lambda label, *args, **kwargs: label == "Stop"
    mock_streamlit.fragment.__module__ = "streamlit.testing"
    mock_streamlit.fragment.side_effect = lambda run_every=0.5: (lambda func: func)

    with patch("apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents), patch(
        "apmatia.interfaces.streamlit.api_client.list_llm_configs", return_value=llm_configs
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_tree",
        return_value=tree,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.discussion_state",
        return_value=snapshot,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.stop_discussion"
    ) as mock_stop:
        import apmatia.interfaces.streamlit.pages.discussion as discussion_page

        discussion_page = importlib.reload(discussion_page)
    discussion_page.render()

    mock_stop.assert_called_once()
    assert mock_streamlit.rerun.call_count >= 1


def test_discussion_history_collapses_older_messages_and_skips_active_message(mock_streamlit):
    """The static transcript should keep only recent messages visible while streaming."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [
            {"role": "User", "text": f"Message {index}"}
            for index in range(10)
        ],
        "activity": {
            "stage": "generating",
            "agent_name": "Planner",
            "speaker_name": "Planner",
        },
        "is_streaming": True,
    }
    rendered = []

    def fake_render_message_card(*args, **kwargs):
        rendered.append(kwargs["card_key"])

    with patch.object(discussion_page, "render_message_card", side_effect=fake_render_message_card):
        discussion_page._render_message_history(
            snapshot,
            username="nick",
            agent_name="Planner",
            active_message_index=9,
        )

    assert rendered == [
        "discussion-IDabc123-0",
        "discussion-IDabc123-1",
        "discussion-IDabc123-2",
        "discussion-IDabc123-3",
        "discussion-IDabc123-4",
        "discussion-IDabc123-5",
        "discussion-IDabc123-6",
        "discussion-IDabc123-7",
        "discussion-IDabc123-8",
    ]
    mock_streamlit.expander.assert_called_once_with("Older messages (1)", expanded=False)


def test_discussion_streaming_view_renders_only_the_active_message(mock_streamlit):
    """The live fragment should update only the in-flight assistant message."""
    import apmatia.interfaces.streamlit.pages.discussion as discussion_page

    discussion_page = importlib.reload(discussion_page)
    snapshot = {
        "discussion_id": "IDabc123",
        "messages": [
            {"role": "User", "text": "Hello"},
            {"role": "Assistant", "text": "Working on it", "speaker_name": "Planner"},
        ],
        "activity": {
            "stage": "generating",
            "agent_name": "Planner",
            "speaker_name": "Planner",
        },
        "llama_server_status": {
            "chat_format": "peg-native",
            "thinking_enabled": False,
            "selected_slot_id": 1,
            "current_task_id": 999,
            "prompt_processing_progress": 0.25,
            "prompt_processing_n_tokens": 128,
            "prompt_tokens_total": 512,
            "prompt_eval": {"tokens_per_second": 44.0},
            "eval": {"tokens_per_second": 8.5},
            "total_time_ms": 2400.0,
            "total_tokens": 256,
            "slots_idle": False,
        },
        "is_streaming": True,
    }
    rendered = []

    def fake_render_message_card(*args, **kwargs):
        rendered.append(kwargs["card_key"])

    with patch.object(discussion_page, "render_message_card", side_effect=fake_render_message_card), patch.object(
        discussion_page, "_render_live_activity_card"
    ) as mock_live_activity:
        returned_snapshot = discussion_page._render_streaming_message_view(
            snapshot,
            username="nick",
            agent_name="Planner",
        )

    assert returned_snapshot is snapshot
    assert rendered == ["discussion-IDabc123-1"]
    mock_live_activity.assert_not_called()


def test_main_function_authenticated_routes_to_settings(mock_streamlit):
    """Authenticated users can navigate to settings through the sidebar."""
    mock_streamlit.sidebar.button.side_effect = lambda label, *args, **kwargs: label == "⚙️ Settings"

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)

    with patch.object(
        app,
        "get_auth_session",
        return_value={"authenticated": True, "username": "testuser"},
    ), patch.object(
        app,
        "get_settings",
        return_value={"theme": "dark"},
    ), patch.object(
        app,
        "list_module_catalog",
        return_value=[],
    ), patch.object(
        app,
        "logout",
    ) as mock_logout, patch(
        "apmatia.interfaces.streamlit.pages.settings.render"
    ) as mock_settings_render:
        app.main()

    assert Path(app.FAVICON_PATH).is_file()
    mock_logout.assert_not_called()
    mock_streamlit.set_page_config.assert_called_once_with(
        page_title="Apmatia", page_icon=str(app.FAVICON_PATH), layout="centered"
    )
    mock_streamlit.set_option.assert_called_once_with(
        "client.showSidebarNavigation", False
    )
    mock_streamlit.sidebar.title.assert_called_once_with("Apmatia")
    assert mock_streamlit.sidebar.button.call_count == 9
    mock_streamlit.sidebar.button.assert_any_call(
        "🧩 AI Models",
        key="nav_model_management",
        use_container_width=True,
        type="secondary",
    )
    mock_streamlit.sidebar.button.assert_any_call(
        "📦 Modules",
        key="nav_module_management",
        use_container_width=True,
        type="secondary",
    )
    mock_streamlit.markdown.assert_called()
    rendered_css = "\n".join(
        call.args[0]
        for call in mock_streamlit.markdown.call_args_list
        if call.args
    )
    assert '[data-testid="stSidebarCollapseButton"]' in rendered_css
    assert '[data-testid="stExpandSidebarButton"]' in rendered_css
    assert '[data-testid="stSidebar"][aria-expanded="false"]' in rendered_css
    assert "pointer-events: auto !important" in rendered_css
    assert "z-index: 2147483645" in rendered_css
    assert "min-width: 2.75rem" in rendered_css
    assert 'div[data-testid="stPopover"]' in rendered_css
    mock_streamlit.popover.assert_called_once_with("⋮", key="apm_header_menu", width=264)
    mock_streamlit.button.assert_any_call(
        "⚙️ Settings", key="header_settings_button", use_container_width=True
    )
    mock_settings_render.assert_called_once()
    assert mock_streamlit.session_state["selected_page"] == "settings"


def test_render_sidebar_shows_visible_module_with_active_subpages(mock_streamlit):
    mock_streamlit.session_state["selected_page"] = "module_view"
    mock_streamlit.session_state["selected_module_id"] = "apmatia_ipe"
    mock_streamlit.session_state["selected_module_view_id"] = "apmatia_ipe.task.view"

    modules = [
        {
            "module_id": "apmatia_ipe",
            "name": "Apmatia IPE",
            "hidden": False,
            "views": [
                {"view_id": "apmatia_ipe.task.view", "name": "Tasks View", "effective_hidden": False},
                {"view_id": "apmatia_ipe.project.view", "name": "Projects View", "effective_hidden": True},
            ],
        },
        {
            "module_id": "hidden_module",
            "name": "Hidden Module",
            "hidden": True,
            "views": [{"view_id": "hidden_module.view", "name": "Hidden View", "effective_hidden": False}],
        },
    ]
    mock_streamlit.sidebar.button.return_value = False

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)

    with patch.object(app, "list_module_catalog", return_value=modules):
        selected_page = app.render_sidebar()

    assert selected_page == "module_view"
    mock_streamlit.sidebar.button.assert_any_call(
        "Apmatia IPE",
        key="nav_module_apmatia_ipe",
        use_container_width=True,
        type="primary",
    )
    mock_streamlit.sidebar.button.assert_any_call(
        "Tasks View",
        key="nav_module_view_apmatia_ipe.task.view",
        use_container_width=True,
        type="primary",
    )
    button_labels = [call.args[0] for call in mock_streamlit.sidebar.button.call_args_list if call.args]
    assert "Projects View" not in button_labels
    assert "Hidden Module" not in button_labels


def test_render_sidebar_clicking_module_selects_first_visible_view(mock_streamlit):
    mock_streamlit.session_state["selected_page"] = "discussion"

    def sidebar_button(label, *args, **kwargs):
        return label == "Apmatia IPE"

    mock_streamlit.sidebar.button.side_effect = sidebar_button
    modules = [
        {
            "module_id": "apmatia_ipe",
            "name": "Apmatia IPE",
            "hidden": False,
            "views": [
                {"view_id": "apmatia_ipe.task.view", "name": "Tasks View", "effective_hidden": False},
                {"view_id": "apmatia_ipe.project.view", "name": "Projects View", "effective_hidden": False},
            ],
        }
    ]

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)

    with patch.object(app, "list_module_catalog", return_value=modules):
        app.render_sidebar()

    assert mock_streamlit.session_state["selected_page"] == "module_view"
    assert mock_streamlit.session_state["selected_module_id"] == "apmatia_ipe"
    assert mock_streamlit.session_state["selected_module_view_id"] == "apmatia_ipe.task.view"
    mock_streamlit.rerun.assert_called_once()


def test_render_sidebar_shows_agent_loops_contact_roster(mock_streamlit):
    mock_streamlit.session_state["selected_page"] = "module_view"
    mock_streamlit.session_state["selected_module_id"] = "apmatia_agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "apmatia_agent_loops.tasks.view"
    mock_streamlit.sidebar.button.return_value = False

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
            ],
        }
    ]
    contact_items = [
        {
            "id": "agent:7",
            "contact_kind": "agent",
            "contact_id": 7,
            "title": "Iris Irving",
            "kind": "Agent",
            "task_count": 2,
            "detail": "Model gpt-4o",
        },
        {
            "id": "group:9",
            "contact_kind": "group",
            "contact_id": 9,
            "title": "Ops",
            "kind": "Group",
            "task_count": 1,
            "detail": "Shared workspace",
        },
    ]

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)

    with patch.object(app, "list_module_catalog", return_value=modules), patch.object(
        app, "list_module_view_items", return_value=contact_items
    ):
        selected_page = app.render_sidebar()

    assert selected_page == "module_view"
    mock_streamlit.sidebar.button.assert_any_call(
        "Back to Apmatia",
        key="agent_loops_exit_top",
        use_container_width=True,
    )
    assert mock_streamlit.session_state["agent_loops_selected_contact_id"] == "agent:7"
    assert "Modules" not in [call.args[0] for call in mock_streamlit.sidebar.subheader.call_args_list if call.args]
    mock_streamlit.rerun.assert_called()


def test_main_function_authenticated_routes_to_agent_management(mock_streamlit):
    """Authenticated users can navigate to the agent page through the sidebar."""
    mock_streamlit.sidebar.button.side_effect = lambda label, *args, **kwargs: label == "🤖 Agents"

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        return_value={"authenticated": True, "username": "testuser"},
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_settings",
        return_value={"theme": "dark"},
    ), patch(
        "apmatia.interfaces.streamlit.pages.agent_management.render"
    ) as mock_agent_render:
        import apmatia.interfaces.streamlit.app as app

        app = importlib.reload(app)
        app.main()

    mock_agent_render.assert_called_once()
    assert mock_streamlit.session_state["selected_page"] == "agent_management"


def test_main_function_authenticated_routes_to_user_management(mock_streamlit):
    """Authenticated users can navigate to the user management page through the sidebar."""
    mock_streamlit.sidebar.button.side_effect = lambda label, *args, **kwargs: label == "👥 Users & Groups"

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        return_value={"authenticated": True, "username": "testuser"},
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_settings",
        return_value={"theme": "dark"},
    ), patch(
        "apmatia.interfaces.streamlit.pages.user_management.render"
    ) as mock_user_render:
        import apmatia.interfaces.streamlit.app as app

        app = importlib.reload(app)
        app.main()

    mock_user_render.assert_called_once()
    assert mock_streamlit.session_state["selected_page"] == "user_management"


def test_header_menu_settings_button_selects_settings_page(mock_streamlit):
    """The top-right menu routes users to settings without a page reload."""
    mock_streamlit.button.side_effect = (
        lambda label, *args, **kwargs: label == "⚙️ Settings"
    )
    mock_streamlit.rerun.side_effect = RuntimeError("rerun")

    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        return_value={"authenticated": True, "username": "testuser"},
    ), patch(
        "apmatia.interfaces.streamlit.api_client.get_settings",
        return_value={"theme": "dark"},
    ):
        import apmatia.interfaces.streamlit.app as app

        app = importlib.reload(app)
        with pytest.raises(RuntimeError, match="rerun"):
            app.main()

    assert mock_streamlit.session_state["selected_page"] == "settings"
    mock_streamlit.rerun.assert_called_once()
    mock_streamlit.sidebar.button.assert_not_called()


def test_main_function_shows_auth_when_unauthenticated(mock_streamlit):
    """Unauthenticated users are sent to the auth page."""
    with patch(
        "apmatia.interfaces.streamlit.api_client.get_auth_session",
        return_value={"authenticated": False, "username": None},
    ), patch(
        "apmatia.interfaces.streamlit.pages.login.show_auth_form"
    ) as mock_show_auth_form:
        import apmatia.interfaces.streamlit.app as app

        app = importlib.reload(app)
        app.main()

    mock_show_auth_form.assert_called_once()


def test_streamlit_container_copies_runtime_config():
    """The image must include Streamlit config so default page discovery stays hidden."""
    config_path = REPO_ROOT / ".streamlit" / "config.toml"

    assert config_path.is_file()
    assert "showSidebarNavigation = false" in config_path.read_text()
    assert 'toolbarMode = "minimal"' in config_path.read_text()
    assert 'base = "dark"' in config_path.read_text()


def test_streamlit_entrypoint_disables_default_sidebar_navigation():
    """The runtime command must explicitly suppress Streamlit's built-in page list."""
    entrypoint = (REPO_ROOT / "scripts" / "entrypoint.sh").read_text()

    assert "--client.showSidebarNavigation false" in entrypoint


def test_start_script_publishes_ports_on_host_loopback_only():
    """The standard launcher must publish ports only on host loopback."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert '-p 127.0.0.1:8000:8000' in launcher
    assert '-p 127.0.0.1:8501:8501' in launcher
    assert '-p 0.0.0.0:8000:8000' not in launcher
    assert '-p 0.0.0.0:8501:8501' not in launcher


def test_start_script_supports_dev_mode():
    """The standard launcher must expose a dev mode that starts both services."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert 'Usage: ./start.sh [core|streamlit|dev]' in launcher
    assert 'core|streamlit|dev' in launcher
    assert 'if [ "$MODE" = "dev" ]; then' in launcher
    assert 'run_core_container_detached "$CORE_IMAGE_NAME" >/dev/null' in launcher
    assert 'run_streamlit_container "$STREAMLIT_IMAGE_NAME"' in launcher


def test_docker_compose_publishes_ports_on_host_loopback_only():
    """Docker Compose must keep the published ports on localhost."""
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    assert '127.0.0.1:8000:8000' in compose
    assert '127.0.0.1:8501:8501' in compose
    assert '8001:8000' not in compose
    assert '0.0.0.0:8000:8000' not in compose
    assert '0.0.0.0:8501:8501' not in compose


def test_docker_launchers_bind_processes_to_container_all_interfaces():
    """Docker launch paths must allow the process to bind inside the container while host publication stays local."""
    launcher = (REPO_ROOT / "start.sh").read_text()
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    assert 'APMATIA_SERVER_HOST=0.0.0.0' in launcher
    assert 'APMATIA_STREAMLIT_HOST=0.0.0.0' in launcher
    assert 'APMATIA_SERVER_TRANSPORT_SECURITY_CONTAINER_HOST_LOOPBACK_ONLY=true' in launcher
    assert 'APMATIA_SERVER_HOST=0.0.0.0' in compose
    assert 'APMATIA_STREAMLIT_HOST=0.0.0.0' in compose
    assert 'APMATIA_SERVER_TRANSPORT_SECURITY_CONTAINER_HOST_LOOPBACK_ONLY=true' in compose


def test_start_script_mounts_persistent_user_state():
    """The standard launcher must mount the same host persistence directories used by compose."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert '-v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR"' in launcher
    assert '-v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR"' in launcher
    assert '-v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR"' in launcher
    assert '-e HOME="$APMATIA_CONTAINER_HOME"' in launcher
    assert '-e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR"' in launcher
    assert '-e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR"' in launcher
    assert '-v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR"' in launcher
    assert '-e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules"' in launcher
    assert '--user "$(id -u):$(id -g)"' in launcher


def test_start_script_bootstraps_workspace_modules_on_the_host():
    """The standard launcher must create the user workspace under ~/.apmatia."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert 'APMATIA_WORKSPACE_DIR_HOST="${APMATIA_WORKSPACE_DIR:-$HOME/.apmatia/workspace}"' in launcher
    assert 'APMATIA_WORKSPACE_ROOT_HOST="$APMATIA_WORKSPACE_DIR_HOST/modules"' in launcher
    assert "repair_host_permissions()" in launcher
    assert 'ensure_host_permissions "$APMATIA_HOME_HOST" "$APMATIA_HOME_HOST"' in launcher
    assert 'ensure_host_permissions "$APMATIA_DATA_DIR_HOST" "$APMATIA_DATA_DIR_HOST"' in launcher
    assert 'ensure_host_permissions "$APMATIA_CONFIG_DIR_HOST" "$APMATIA_CONFIG_DIR_HOST"' in launcher
    assert 'mkdir -p "$APMATIA_WORKSPACE_ROOT_HOST"' in launcher
    assert 'mkdir -p "$APMATIA_HOME_HOST/workspace/modules"' not in launcher


def test_start_script_uses_saved_llama_server_log_dir_when_env_is_missing():
    """The standard launcher should fall back to the saved config for llama.cpp logs."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert "config.json" in launcher
    assert "llama_server" in launcher


def test_start_script_mounts_saved_gguf_directory_when_env_is_missing():
    """The standard launcher should mount the saved GGUF directory into the container."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert 'APMATIA_GGUF_DIRECTORIES_HOST="${APMATIA_GGUF_DIRECTORIES:-}"' in launcher
    assert "ai_model_manager" in launcher
    assert "gguf_directory" in launcher
    assert "gguf_directories" in launcher
    assert '-e APMATIA_GGUF_DIRECTORIES="$GGUF_DIRECTORY_ENV"' in launcher


def test_windows_launcher_bootstraps_persistent_directories():
    """The Windows launcher must create the same directories before compose starts."""
    launcher = (REPO_ROOT / "scripts" / "start.bat").read_text()

    assert 'mkdir "%USERPROFILE%\\.apmatia\\workspace\\modules"' in launcher
    assert 'mkdir "%USERPROFILE%\\.apmatia"' in launcher
    assert 'mkdir "%USERPROFILE%\\.config\\apmatia"' in launcher
    assert 'mkdir "%USERPROFILE%\\.local\\share\\apmatia"' in launcher


def test_container_has_writable_non_root_home():
    """The image must support running mounted local state as the host user."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()

    assert "mkdir -p /home/apmatia" in dockerfile
    assert "useradd --uid 1000 --gid 1000" in dockerfile
    assert "chown -R apmatia:apmatia /home/apmatia" in dockerfile
    assert "USER apmatia" in dockerfile
