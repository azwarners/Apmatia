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
        if label == "Tool group":
            return "Tool management"
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
    mock_streamlit.write.assert_any_call("**Apmatia administration**")
    mock_streamlit.write.assert_any_call("**Tool management**")
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
            call(7, 2, enabled=True, confirmation_required=None, read_only=None),
            call(7, 1, enabled=True, confirmation_required=None, read_only=None),
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

def test_ai_model_manager_module_view_shows_saved_model_url():
    """The migrated module view returns the saved model URL for its API URL column."""
    from apmatia.core.module_view_runtime import ModuleViewContext
    from apmatia.modules.ai_model_manager.models import LLMConfig
    from apmatia.modules.ai_model_manager.module_views import ApmatiaAiModelManagerModuleViewProvider
    from apmatia.modules.ai_model_manager.views import VIEW_DESCRIPTORS

    config = LLMConfig(
        id=1,
        user_alias="Local Model",
        backend="openai_compatible",
        provider_name="Qwen",
        model_url="http://localhost:5001",
    )
    view = next(item for item in VIEW_DESCRIPTORS if item.view_id == "ai_model_manager.llm_configs.view")
    with patch("apmatia.modules.ai_model_manager.module_views.list_llm_configs", return_value=[config]):
        items = ApmatiaAiModelManagerModuleViewProvider().list_items(
            view=view,
            context=ModuleViewContext(user_id=1),
        )

    assert items[0]["model_url"] == "http://localhost:5001"
    assert {column["key"]: column["label"] for column in view.metadata["ui"]["columns"]}["model_url"] == "API URL"

def test_ai_model_manager_module_view_can_test_ai_model():
    """The migrated module view probes a saved AI model through its test command."""
    from apmatia.core.module_view_runtime import ModuleViewContext
    from apmatia.modules.ai_model_manager.commands import COMMAND_DESCRIPTORS
    from apmatia.modules.ai_model_manager.module_views import ApmatiaAiModelManagerModuleViewProvider

    command = next(item for item in COMMAND_DESCRIPTORS if item.command_id == "ai_model_manager.llm_configs.test")
    with patch(
        "apmatia.modules.ai_model_manager.module_views.probe_llm_config",
        return_value={"reply_preview": "ready and connected"},
    ) as mock_test:
        result = ApmatiaAiModelManagerModuleViewProvider().execute_command(
            command=command,
            payload={"item_id": 1},
            context=ModuleViewContext(user_id=1),
        )

    mock_test.assert_called_once_with(1)
    assert result == {"status": "ok", "item": {"reply_preview": "ready and connected"}}

def test_ai_model_manager_module_view_uses_ai_model_labels():
    """The migrated module view exposes current LLM configuration labels and commands."""
    from apmatia.modules.ai_model_manager.views import VIEW_DESCRIPTORS

    view = next(item for item in VIEW_DESCRIPTORS if item.view_id == "ai_model_manager.llm_configs.view")
    ui = view.metadata["ui"]

    assert ui["title"] == "LLM Configs"
    assert ui["caption"] == "Manage remote LLM endpoint configurations (OpenAI-compatible APIs)."
    assert view.metadata["singular_label"] == "LLM Config"
    assert view.metadata["plural_label"] == "LLM Configs"
    assert ui["commands"] == {
        "create": "ai_model_manager.llm_configs.create",
        "edit": "ai_model_manager.llm_configs.edit",
        "delete": "ai_model_manager.llm_configs.delete",
    }

def test_user_management_page_loads_and_manages_groups(mock_streamlit):
    """User management uses the API client for users, groups, and membership updates."""
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 1, "username": "nick"}
    mock_streamlit.session_state["user_management_selected_group_id"] = 10
    mock_streamlit.form_submit_button.side_effect = [True, False, False, False, False]
    mock_streamlit.text_input.side_effect = ["newuser", "newpass", "nick", "", "team"]
    mock_streamlit.text_area.return_value = "Team description"
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.button.return_value = False

    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Member type":
            return "agent"
        if label == "Agent" and options:
            return options[0]
        if label == "Role":
            return "member"
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect

    users = [
        {"id": 1, "username": "nick", "is_enabled": True},
        {"id": 2, "username": "alice", "is_enabled": False},
    ]
    agents = [{"id": 77, "name": "Planner"}]
    groups = [
        {"id": 10, "name": "team", "description": "Team description", "created_by_user_id": 1},
        {"id": 11, "name": "other", "description": "", "created_by_user_id": 2},
    ]
    memberships = [
        {"id": 100, "group_id": 10, "user_id": 1, "role": "owner", "is_enabled": True},
        {"id": 101, "group_id": 10, "user_id": 2, "role": "member", "is_enabled": True},
        {"id": 102, "group_id": 10, "agent_id": 77, "member_kind": "agent", "role": "member", "is_enabled": True},
    ]

    with patch("apmatia.interfaces.streamlit.api_client.list_users", return_value=users), patch(
        "apmatia.interfaces.streamlit.api_client.list_groups", return_value=groups
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents
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

def test_user_management_page_allows_adding_agent_members(mock_streamlit):
    """Group member selection should switch to agents and submit an agent payload."""
    mock_streamlit.session_state["authenticated_user"] = {"user_id": 1, "username": "nick"}
    mock_streamlit.session_state["user_management_selected_group_id"] = 10
    mock_streamlit.form_submit_button.side_effect = [False, False, False, True]
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.text_area.return_value = ""
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.button.return_value = False

    def selectbox_side_effect(label, options, index=0, **_kwargs):
        if label == "Member type":
            return "agent"
        if label == "Agent":
            return options[0]
        if label == "Role":
            return "member"
        return options[index]

    mock_streamlit.selectbox.side_effect = selectbox_side_effect

    users = [{"id": 1, "username": "nick", "is_enabled": True}]
    agents = [{"id": 77, "name": "Planner"}]
    groups = [{"id": 10, "name": "team", "description": "Team description", "created_by_user_id": 1}]
    memberships = [{"id": 100, "group_id": 10, "user_id": 1, "role": "owner", "is_enabled": True}]

    with patch("apmatia.interfaces.streamlit.api_client.list_users", return_value=users), patch(
        "apmatia.interfaces.streamlit.api_client.list_groups", return_value=groups
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_agents", return_value=agents
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_user"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.update_user"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.delete_user"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.create_group"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.update_group"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.delete_group"
    ), patch(
        "apmatia.interfaces.streamlit.api_client.list_group_members",
        return_value=memberships,
    ), patch(
        "apmatia.interfaces.streamlit.api_client.add_group_member"
    ) as mock_add_group_member, patch(
        "apmatia.interfaces.streamlit.api_client.set_group_membership_enabled"
    ):
        import apmatia.interfaces.streamlit.pages.user_management as user_management_page

        user_management_page = importlib.reload(user_management_page)
        user_management_page.render()

    mock_add_group_member.assert_called_once_with(
        10,
        member_kind="agent",
        role="member",
        agent_id=77,
    )

def test_message_text_blocks_preserve_markdown_and_emoji(mock_streamlit):
    import apmatia.interfaces.streamlit.components.message_card as message_card

    importlib.reload(message_card)
    message_card.render_message_text_block("Hello **world**\nLine two 😀")

    mock_streamlit.markdown.assert_called_once_with("Hello **world**\nLine two 😀")

def test_contacts_shell_creates_fresh_discussion_for_agent_contact(mock_streamlit):
    """Selecting an agent contact should create a fresh contacts discussion."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    contact = {"contact_id": "agent:7", "contact_type": "agent", "label": "Planner"}

    with patch.object(streamlit_app, "discussion_tree", create=True) as mock_tree, patch.object(
        streamlit_app, "open_discussion"
    ) as mock_open, patch.object(streamlit_app, "create_discussion", return_value={"discussion": {"discussion_id": "IDnew123"}}) as mock_create:
        streamlit_app._activate_contacts_contact(contact)

    assert mock_streamlit.session_state["contacts_shell_active"] is True
    assert mock_streamlit.session_state["contacts_active_discussion_id"] == "IDnew123"
    assert mock_streamlit.session_state["contacts_contact_discussion_ids"]["agent:7"] == "IDnew123"
    mock_tree.assert_called_once()
    mock_create.assert_called_once_with(
        title="Planner",
        chat_mode="round_robin",
        agent_id=7,
        participant_agent_ids=[7],
    )
    mock_open.assert_called_once_with("IDnew123")

def test_selecting_contacts_module_restores_contacts_shell(mock_streamlit):
    """Contacts uses its roster sidebar instead of the generic Chat Targets view."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    with patch.object(streamlit_app, "_render_contacts_sidebar", return_value="discussion") as mock_contacts_sidebar:
        streamlit_app._select_module_for_navigation("contacts_and_discussions", [])

    assert mock_streamlit.session_state["selected_page"] == "discussion"
    assert mock_streamlit.session_state["selected_module_id"] == "contacts_and_discussions"
    assert mock_streamlit.session_state["selected_module_view_id"] == "contacts_and_discussions.chat_targets.view"
    assert mock_streamlit.session_state["contacts_shell_active"] is True
    mock_streamlit.rerun.assert_called_once()

    with patch.object(streamlit_app, "_render_contacts_sidebar", return_value="discussion") as mock_contacts_sidebar:
        selected_page = streamlit_app.render_sidebar()
    assert selected_page == "discussion"
    mock_contacts_sidebar.assert_called_once()

def test_contacts_shell_reopens_existing_discussion_for_agent_contact(mock_streamlit):
    """Refreshing an agent contact should reopen the prior discussion instead of creating a new one."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    contact = {"contact_id": "agent:7", "contact_type": "agent", "label": "Planner"}
    tree = {
        "discussions": [
            {
                "discussion_id": "IDagentexisting",
                "title": "Planner",
                "participant_agent_ids": [7],
                "updated_at": "2026-07-17T12:00:00+00:00",
            }
        ]
    }

    with patch.object(streamlit_app, "discussion_tree", return_value=tree) as mock_tree, patch.object(
        streamlit_app,
        "open_discussion",
    ) as mock_open, patch.object(streamlit_app, "create_discussion") as mock_create:
        streamlit_app._activate_contacts_contact(contact)

    assert mock_streamlit.session_state["contacts_active_discussion_id"] == "IDagentexisting"
    assert mock_streamlit.session_state["contacts_contact_discussion_ids"]["agent:7"] == "IDagentexisting"
    mock_tree.assert_called_once()
    mock_open.assert_called_once_with("IDagentexisting")
    mock_create.assert_not_called()

def test_contacts_shell_creates_fresh_discussion_for_group_contact(mock_streamlit):
    """Selecting a group contact should create a fresh contacts discussion."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    contact = {"contact_id": "group:9", "contact_type": "group", "label": "DevTeam"}

    with patch.object(streamlit_app, "discussion_tree", create=True) as mock_tree, patch.object(
        streamlit_app, "open_discussion"
    ) as mock_open, patch.object(
        streamlit_app,
        "create_discussion",
        return_value={"discussion": {"discussion_id": "IDgroupnew123"}},
    ) as mock_create:
        streamlit_app._activate_contacts_contact(contact)

    assert mock_streamlit.session_state["contacts_shell_active"] is True
    assert mock_streamlit.session_state["contacts_active_discussion_id"] == "IDgroupnew123"
    assert mock_streamlit.session_state["contacts_contact_discussion_ids"]["group:9"] == "IDgroupnew123"
    mock_tree.assert_called_once()
    mock_create.assert_called_once_with(
        title="DevTeam",
        chat_mode="round_robin",
        group_id=9,
    )
    mock_open.assert_called_once_with("IDgroupnew123")

def test_contacts_shell_reopens_existing_discussion_for_group_contact(mock_streamlit):
    """Refreshing a group contact should reopen the prior discussion instead of creating a new one."""
    mock_streamlit.session_state.clear()

    import apmatia.interfaces.streamlit.app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    contact = {"contact_id": "group:9", "contact_type": "group", "label": "DevTeam"}
    tree = {
        "discussions": [
            {
                "discussion_id": "IDgroupexisting",
                "title": "DevTeam",
                "group_id": 9,
                "updated_at": "2026-07-17T12:00:00+00:00",
            }
        ]
    }

    with patch.object(streamlit_app, "discussion_tree", return_value=tree) as mock_tree, patch.object(
        streamlit_app,
        "open_discussion",
    ) as mock_open, patch.object(streamlit_app, "create_discussion") as mock_create:
        streamlit_app._activate_contacts_contact(contact)

    assert mock_streamlit.session_state["contacts_active_discussion_id"] == "IDgroupexisting"
    assert mock_streamlit.session_state["contacts_contact_discussion_ids"]["group:9"] == "IDgroupexisting"
    mock_tree.assert_called_once()
    mock_open.assert_called_once_with("IDgroupexisting")
    mock_create.assert_not_called()

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

def test_contacts_sidebar_filters_to_selected_group_members_and_highlights_current_speaker(mock_streamlit):
    """Group contacts should only show their members, with the active speaker highlighted."""
    mock_streamlit.session_state["contacts_shell_active"] = True
    mock_streamlit.session_state["contacts_active_contact_id"] = "group:9"
    mock_streamlit.session_state["contacts_active_contact_label"] = "DevTeam"
    mock_streamlit.session_state["contacts_active_contact_type"] = "group"
    mock_streamlit.session_state["contacts_active_discussion_id"] = "IDgroupchat"

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)
    contacts = [
        {"contact_id": "agent:1", "contact_type": "agent", "label": "Ada the Architect"},
        {"contact_id": "agent:2", "contact_type": "agent", "label": "Beatrice the Coder"},
        {"contact_id": "agent:3", "contact_type": "agent", "label": "Chloe the Tester"},
        {"contact_id": "group:9", "contact_type": "group", "label": "DevTeam"},
    ]
    group_members = [
        {"member_kind": "agent", "agent_id": 2, "is_enabled": True},
        {"member_kind": "user", "user_id": 77, "is_enabled": True},
    ]

    with patch.object(app, "_contact_roster", return_value=contacts), patch.object(
        app,
        "list_group_members",
        return_value=group_members,
    ), patch.object(
        app,
        "discussion_state",
        return_value={
            "discussion_id": "IDgroupchat",
            "activity": {"stage": "generating", "speaker_name": "Beatrice the Coder"},
        },
    ):
        app._render_contacts_sidebar()

    button_calls = mock_streamlit.sidebar.button.call_args_list
    assert any(call.args and call.args[0] == "DevTeam" and call.kwargs.get("type") == "primary" for call in button_calls)
    assert any(
        call.args and call.args[0] == "Beatrice the Coder" and call.kwargs.get("type") == "primary"
        for call in button_calls
    )
    assert not any(call.args and call.args[0] == "Ada the Architect" for call in button_calls)
    assert not any(call.args and call.args[0] == "Chloe the Tester" for call in button_calls)
    mock_streamlit.sidebar.caption.assert_any_call("Showing members of DevTeam.")

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
    assert mock_streamlit.sidebar.button.call_count == 5
    mock_streamlit.sidebar.button.assert_any_call(
        "📦 Modules",
        key="nav_module_management",
        use_container_width=True,
        type="primary",
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
    mock_streamlit.session_state["selected_module_id"] = "ipe"
    mock_streamlit.session_state["selected_module_view_id"] = "ipe.task.view"

    modules = [
        {
            "module_id": "ipe",
            "name": "Integrated Productivity Environment",
            "hidden": False,
            "views": [
                {"view_id": "ipe.task.view", "name": "Tasks View", "effective_hidden": False},
                {"view_id": "ipe.project.view", "name": "Projects View", "effective_hidden": True},
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
        "Integrated Productivity Environment",
        key="nav_module_ipe",
        use_container_width=True,
        type="primary",
    )
    mock_streamlit.sidebar.button.assert_any_call(
        "Tasks View",
        key="nav_module_view_ipe.task.view",
        use_container_width=True,
        type="primary",
    )
    button_labels = [call.args[0] for call in mock_streamlit.sidebar.button.call_args_list if call.args]
    assert "Projects View" not in button_labels
    assert "Hidden Module" not in button_labels

def test_render_sidebar_clicking_module_selects_first_visible_view(mock_streamlit):
    mock_streamlit.session_state["selected_page"] = "discussion"

    def sidebar_button(label, *args, **kwargs):
        return label == "Integrated Productivity Environment"

    mock_streamlit.sidebar.button.side_effect = sidebar_button
    modules = [
        {
            "module_id": "ipe",
            "name": "Integrated Productivity Environment",
            "hidden": False,
            "views": [
                {"view_id": "ipe.task.view", "name": "Tasks View", "effective_hidden": False},
                {"view_id": "ipe.project.view", "name": "Projects View", "effective_hidden": False},
            ],
        }
    ]

    import apmatia.interfaces.streamlit.app as app

    app = importlib.reload(app)

    with patch.object(app, "list_module_catalog", return_value=modules):
        app.render_sidebar()

    assert mock_streamlit.session_state["selected_page"] == "module_view"
    assert mock_streamlit.session_state["selected_module_id"] == "ipe"
    assert mock_streamlit.session_state["selected_module_view_id"] == "ipe.task.view"
    mock_streamlit.rerun.assert_called_once()

def test_render_sidebar_shows_agent_loops_contact_roster(mock_streamlit):
    mock_streamlit.session_state["selected_page"] = "module_view"
    mock_streamlit.session_state["selected_module_id"] = "agent_loops"
    mock_streamlit.session_state["selected_module_view_id"] = "agent_loops.tasks.view"
    mock_streamlit.sidebar.button.return_value = False

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
                    "module_id": "agent_loops",
                    "view_id": "agent_loops.tasks.view",
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

def test_main_function_reuses_generation_for_same_module_view(mock_streamlit):
    """Rendering the same module view keeps its generation-scoped shell stable."""

    class _Container:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    mock_streamlit.container.side_effect = lambda **_kwargs: _Container()

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
        "initialize_ui_preferences",
    ), patch.object(
        app,
        "apply_theme_styles",
    ), patch.object(
        app,
        "_process_header_actions",
    ), patch.object(
        app,
        "render_top_bar",
    ), patch.object(
        app,
        "render_sidebar",
        side_effect=["module_view", "module_view"],
    ), patch.object(
        app,
        "ensure_ipe_coach_agent_for_user",
    ), patch(
        "apmatia.interfaces.streamlit.pages.module_views.render",
    ) as mock_module_views_render:
        app.main()
        app.main()

    assert mock_module_views_render.call_count == 2
    shell_keys = [kwargs.get("key") for _args, kwargs in mock_streamlit.container.call_args_list]
    assert len(shell_keys) == 2
    assert shell_keys[0].startswith("apm-page-shell:module_view:")
    assert shell_keys[1].startswith("apm-page-shell:module_view:")
    first_generation = int(shell_keys[0].rsplit(":", 1)[-1])
    second_generation = int(shell_keys[1].rsplit(":", 1)[-1])
    assert second_generation == first_generation

def test_main_function_restarts_shell_when_module_view_detail_changes(mock_streamlit):
    """Changing the module-view detail while staying on module_view should still refresh the shell."""

    class _Container:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    mock_streamlit.container.side_effect = lambda **_kwargs: _Container()

    module_view_states = [
        ("agent_loops", "agent_loops.tasks.view"),
        ("agent_alarms", "agent_alarms.alarms.view"),
    ]

    def _render_sidebar():
        selected_module_id, selected_module_view_id = module_view_states.pop(0)
        mock_streamlit.session_state["selected_page"] = "module_view"
        mock_streamlit.session_state["selected_module_id"] = selected_module_id
        mock_streamlit.session_state["selected_module_view_id"] = selected_module_view_id
        return "module_view"

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
        "initialize_ui_preferences",
    ), patch.object(
        app,
        "apply_theme_styles",
    ), patch.object(
        app,
        "_process_header_actions",
    ), patch.object(
        app,
        "render_top_bar",
    ), patch.object(
        app,
        "render_sidebar",
        side_effect=_render_sidebar,
    ), patch.object(
        app,
        "ensure_ipe_coach_agent_for_user",
    ), patch(
        "apmatia.interfaces.streamlit.pages.module_views.render",
    ) as mock_module_views_render:
        app.main()
        app.main()

    assert mock_module_views_render.call_count == 2
    shell_keys = [kwargs.get("key") for _args, kwargs in mock_streamlit.container.call_args_list]
    assert len(shell_keys) == 2
    assert shell_keys[0].startswith("apm-page-shell:module_view:")
    assert shell_keys[1].startswith("apm-page-shell:module_view:")
    first_generation = int(shell_keys[0].rsplit(":", 1)[-1])
    second_generation = int(shell_keys[1].rsplit(":", 1)[-1])
    assert second_generation == first_generation + 1

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

def test_start_script_defaults_to_loopback_and_supports_remote_bind_override():
    """The launcher defaults safely but can publish through a trusted VPN when requested."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert 'APMATIA_DOCKER_BIND_HOST="${APMATIA_DOCKER_BIND_HOST:-127.0.0.1}"' in launcher
    assert '-p "$APMATIA_DOCKER_BIND_HOST":8000:8000' in launcher
    assert '-p "$APMATIA_DOCKER_BIND_HOST":8501:8501' in launcher
    assert 'APMATIA_SERVER_TRANSPORT_SECURITY_ALLOW_INSECURE_NON_LOOPBACK=true' in launcher

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
    assert 'HOME=/home/apmatia' in compose
    assert 'APMATIA_HOME=/home/apmatia/.apmatia' in compose
    assert 'APMATIA_WORKSPACE_ROOT=/home/apmatia/.apmatia/workspace/modules' in compose

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
    assert 'APMATIA_CONTAINER_HOME="/home/apmatia"' in launcher
    assert '--user "$(id -u):$(id -g)"' in launcher

def test_start_script_bootstraps_workspace_modules_on_the_host():
    """The standard launcher must create the user workspace under ~/.apmatia."""
    launcher = (REPO_ROOT / "start.sh").read_text()

    assert 'APMATIA_WORKSPACE_DIR_HOST="${APMATIA_WORKSPACE_DIR:-$HOME/.apmatia/workspace}"' in launcher
    assert 'APMATIA_WORKSPACE_ROOT_HOST="$APMATIA_WORKSPACE_DIR_HOST/modules"' in launcher
    assert "repair_host_permissions()" in launcher
    assert 'ensure_host_permissions "$APMATIA_HOME_HOST" "$APMATIA_CONTAINER_HOME_DIR"' in launcher
    assert 'ensure_host_permissions "$APMATIA_DATA_DIR_HOST" "$APMATIA_CONTAINER_DATA_DIR"' in launcher
    assert 'ensure_host_permissions "$APMATIA_CONFIG_DIR_HOST" "$APMATIA_CONTAINER_CONFIG_DIR"' in launcher
    assert 'mkdir -p "$APMATIA_WORKSPACE_ROOT_HOST"' in launcher
    assert 'mkdir -p "$APMATIA_HOME_HOST/workspace/modules"' not in launcher
    assert 'APMATIA_CONTAINER_HOME="/home/apmatia"' in launcher

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
