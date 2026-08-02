"""Phase 2 acceptance tests for the Linux Flet authentication slice."""

from __future__ import annotations

from unittest.mock import Mock, patch

import flet as ft

from apmatia.interfaces.flet.linux.shell import ApmatiaShell
from apmatia.interfaces.flet.common.renderer import ViewRenderer


def _login_document() -> dict:
    return {
        "view_id": "auth.login.view",
        "title": "Sign In",
        "actions": [{"key": "login", "payload": {"auth_action": "login"}}],
        "presentation": {
            "component_type": "page",
            "children": [
                {
                    "component_type": "form",
                    "properties": {
                        "title": "Sign In",
                        "actions": [{"key": "login", "label": "Sign In"}],
                    },
                    "children": [
                        {"component_type": "field", "properties": {"key": "username", "label": "Username"}},
                        {
                            "component_type": "field",
                            "properties": {"key": "password", "label": "Password", "field_type": "password"},
                        },
                    ],
                }
            ],
        },
    }


class FakePage:
    def __init__(self) -> None:
        self.controls: list[ft.Control] = []
        self.route = "/"

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        pass


def _api(*, authenticated: bool = False) -> Mock:
    api = Mock()
    api.get_session.return_value = {
        "authenticated": authenticated,
        "user_id": 7 if authenticated else None,
        "username": "testuser" if authenticated else None,
    }
    api.get_auth_views.return_value = [_login_document()]
    return api


def test_start_resolves_anonymous_session_to_real_login_view() -> None:
    page = FakePage()
    api = _api()
    shell = ApmatiaShell(page, api)

    shell.start()

    assert page.route == "/login"
    assert not shell._state.is_authenticated
    assert page.controls[0].content is not None
    assert page.controls[0].content.controls
    assert api.get_auth_views.called


def test_login_payload_establishes_session_and_protected_route() -> None:
    page = FakePage()
    api = _api()
    api.login.return_value = {"status": "authenticated", "username": "testuser"}
    api.get_session.side_effect = [
        {"authenticated": False, "user_id": None, "username": None},
        {"authenticated": True, "user_id": 7, "username": "testuser"},
    ]
    shell = ApmatiaShell(page, api)
    shell.start()

    shell._handle_login({"auth_action": "login", "username": "testuser", "password": "secret"})

    api.login.assert_called_once_with("testuser", "secret")
    assert page.route == "/"
    assert shell._state.is_authenticated
    assert shell._state.username == "testuser"


def test_invalid_credentials_do_not_create_authenticated_state() -> None:
    page = FakePage()
    api = _api()
    from apmatia.interfaces.flet.common.errors import AuthenticationError

    api.login.side_effect = AuthenticationError("Invalid credentials.")
    shell = ApmatiaShell(page, api)
    shell.start()

    shell._handle_login({"auth_action": "login", "username": "testuser", "password": "wrong"})

    assert page.route == "/login"
    assert not shell._state.is_authenticated
    assert page.controls[0].content.controls[1].value == "Invalid credentials."


def test_protected_route_redirects_when_session_is_cleared() -> None:
    page = FakePage()
    api = _api(authenticated=True)
    shell = ApmatiaShell(page, api)
    shell.start()

    shell._state.clear_authentication()
    page.route = "/"
    shell.render_route()

    assert page.route == "/login"
    assert page.controls[0].content.controls


def test_logout_clears_session_and_returns_to_login() -> None:
    page = FakePage()
    api = _api(authenticated=True)
    shell = ApmatiaShell(page, api)
    shell.start()

    shell._handle_logout()

    api.logout.assert_called_once_with()
    assert page.route == "/login"
    assert not shell._state.is_authenticated
    assert page.controls[0].content.controls


def test_login_form_dispatches_click_and_enter_to_the_same_intent() -> None:
    intents: list[dict[str, str]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "page",
            "children": [
                {
                    "component_type": "form",
                    "properties": {"actions": [{"label": "Sign In", "payload": {"auth_action": "login"}}]},
                    "children": [
                        {"component_type": "field", "properties": {"key": "username", "label": "Username"}},
                        {
                            "component_type": "field",
                            "properties": {"key": "password", "label": "Password", "field_type": "password"},
                        },
                    ],
                }
            ],
        }
    )
    form = root.content.controls[0]
    username, password, button = form.content.controls[0:3]
    username.value = "nick"
    password.value = "secret"

    button.on_click(None)
    password.on_submit(None)

    assert intents == [
        {"auth_action": "login", "username": "nick", "password": "secret"},
        {"auth_action": "login", "username": "nick", "password": "secret"},
    ]


def test_login_view_preserves_authentication_intent_payload() -> None:
    prepared = ApmatiaShell._login_presentation(_login_document())

    action = prepared["children"][0]["properties"]["actions"][0]

    assert action["payload"] == {"auth_action": "login"}


def test_generic_collection_renderer_binds_rows_and_item_actions() -> None:
    intents: list[dict[str, object]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "page",
            "children": [
                {
                    "component_type": "collection",
                    "binding": {"source": "users", "path": "items"},
                    "properties": {"columns": [{"key": "username", "label": "Username"}]},
                    "action_keys": ["delete"],
                }
            ],
        },
        actions={"delete": {"key": "delete", "label": "Delete", "payload": {"command_id": "users.delete"}}},
        data_sources={"users": {"items": [{"id": 7, "username": "nick"}]}},
        view_id="users.users.view",
    )

    collection = root.content.controls[0]
    delete_button = collection.content.controls[1].controls[1]
    delete_button.on_click(None)

    assert intents == [
        {
            "command_id": "users.delete",
            "item": {"id": 7, "username": "nick"},
            "item_id": 7,
            "__action_key": "delete",
            "__view_id": "users.users.view",
        }
    ]


def test_generic_collection_renderer_accepts_plain_list_for_items_binding() -> None:
    root = ViewRenderer(lambda _intent: None).render(
        {
            "component_type": "collection",
            "binding": {"source": "users", "path": "items"},
            "properties": {"columns": [{"key": "username", "label": "Username"}]},
        },
        data_sources={"users": [{"id": 7, "username": "nick"}]},
        view_id="users.users.view",
    )

    assert len(root.content.controls) == 3
    assert root.content.controls[1].controls[0].value == "nick"


def test_generic_renderer_merges_document_action_command_ids_for_item_actions() -> None:
    intents: list[dict[str, object]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "table",
            "binding": {"source": "items", "path": "items"},
            "properties": {"columns": [{"key": "name", "label": "Name"}], "item_action_keys": ["delete"]},
        },
        actions={"delete": {"key": "delete", "label": "Delete", "command_id": "example.delete"}},
        data_sources={"items": [{"id": 4, "name": "Old model"}]},
        view_id="example.items.view",
    )

    root.content.controls[1].controls[1].on_click(None)

    assert intents[0]["command_id"] == "example.delete"


def test_login_fallback_intent_is_accepted_without_action_marker() -> None:
    page = FakePage()
    api = _api()
    api.login.return_value = {"status": "authenticated", "username": "testuser"}
    api.get_session.side_effect = [
        {"authenticated": False, "user_id": None, "username": None},
        {"authenticated": True, "user_id": 7, "username": "testuser"},
    ]
    shell = ApmatiaShell(page, api, core_version="1.2.3")
    shell.start()

    shell._handle_intent({"username": "testuser", "password": "secret"})

    api.login.assert_called_once_with("testuser", "secret")
    assert page.route == "/"


def test_authenticated_shell_loads_catalog_and_resolves_portable_view() -> None:
    page = FakePage()
    api = _api(authenticated=True)
    api.list_modules.return_value = [
        {
            "module_id": "example",
            "name": "Example",
            "hidden": False,
            "views": [
                {
                    "view_id": "example.items.view",
                    "name": "Items",
                    "effective_hidden": False,
                    "metadata": {},
                }
            ],
        }
    ]
    api.get_module_view_document.return_value = {
        "view_id": "example.items.view",
        "title": "Items",
        "presentation": {"component_type": "page", "children": []},
    }
    shell = ApmatiaShell(page, api)

    shell.start()
    shell._navigate("/view/example.items.view")

    api.list_modules.assert_called_once_with()
    api.get_module_view_document.assert_called_once_with("example.items.view")
    assert page.route == "/view/example.items.view"


def test_sidebar_resize_is_clamped_to_desktop_bounds() -> None:
    page = FakePage()
    shell = ApmatiaShell(page, _api(authenticated=True))

    shell._resize_sidebar(Mock(delta_x=500))
    assert shell._sidebar_width == 480
    shell._resize_sidebar(Mock(delta_x=-500))
    assert shell._sidebar_width == 200


def test_sidebar_resize_uses_flet_pan_local_delta() -> None:
    page = FakePage()
    shell = ApmatiaShell(page, _api(authenticated=True))

    shell._resize_sidebar(Mock(local_delta=Mock(x=40)))

    assert shell._sidebar_width == 300


def test_sidebar_resize_updates_existing_control_without_rebuilding_shell() -> None:
    page = FakePage()
    shell = ApmatiaShell(page, _api(authenticated=True))
    shell._render_shell(ft.Container(), title="Test")
    original_sidebar = shell._sidebar_control

    shell._resize_sidebar(Mock(local_delta=Mock(x=40)))

    assert shell._sidebar_control is original_sidebar
    assert shell._sidebar_control.width == 300


def test_unsupported_intent_logging_does_not_include_credentials() -> None:
    page = FakePage()
    api = _api()
    shell = ApmatiaShell(page, api)

    with patch("apmatia.interfaces.flet.linux.shell.logger.warning") as warning:
        shell._handle_intent({"username": "nick", "password": "secret", "unexpected": True})

    message = " ".join(str(argument) for call in warning.call_args_list for argument in call.args)
    assert "nick" not in message
    assert "secret" not in message
    assert "password" not in message


def test_authenticated_module_errors_offer_a_retry_action() -> None:
    page = FakePage()
    shell = ApmatiaShell(page, _api(authenticated=True))
    shell._state.set_authenticated({"user_id": 7, "username": "testuser"})
    shell._show_error("Core is unavailable")

    assert page.controls[0].content.controls[-1].content == "Retry"


def test_discussion_timeline_preserves_server_message_order() -> None:
    root = ViewRenderer(lambda _intent: None).render(
        {
            "component_type": "timeline",
            "binding": {"source": "messages", "path": "items"},
        },
        data_sources={
            "messages": {
                "items": [
                    {"turn_kind": "user", "text": "First"},
                    {"turn_kind": "assistant", "text": "Second"},
                ]
            }
        },
        view_id="discuss.discussion.view",
    )

    cards = root.controls
    assert [card.content.content.controls[1].value for card in cards] == ["First", "Second"]


def test_discussion_fields_use_stable_state_keys_and_refresh_on_selection() -> None:
    intents: list[dict[str, object]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "field",
            "component_id": "discussion-select-field",
            "properties": {
                "label": "Discussion",
                "field_type": "select",
                "binding_source": "discussions",
            },
        },
        data_sources={"discussions": [{"discussion_id": "d-1"}]},
        state={},
        view_id="discuss.discussion.view",
    )

    root.on_select(Mock(control=root, value="d-1"))

    assert intents == [{"__view_id": "discuss.discussion.view", "__state_update": {"selected_discussion_id": "d-1"}}]


def test_discussion_send_action_resolves_state_payload() -> None:
    intents: list[dict[str, object]] = []
    button = ViewRenderer(intents.append).render(
        {
            "component_type": "actions",
            "properties": {"label": "Send message"},
            "action_keys": ("send_message",),
        },
        actions={
            "send_message": {
                "key": "send_message",
                "payload": {
                    "api_operation": "discussion_prompt",
                    "prompt": "$state.message_input",
                    "discussion_id": "$state.selected_discussion_id",
                },
            }
        },
        state={"message_input": "Hello", "selected_discussion_id": "d-1"},
        view_id="discuss.discussion.view",
    )

    button.controls[0].on_click(None)

    assert intents[0]["api_operation"] == "discussion_prompt"
    assert intents[0]["prompt"] == "Hello"
    assert intents[0]["discussion_id"] == "d-1"


def test_multiselect_uses_flet_compatible_checkboxes() -> None:
    intents: list[dict[str, object]] = []
    control = ViewRenderer(intents.append).render(
        {
            "component_type": "field",
            "component_id": "participant-multiselect",
            "properties": {
                "label": "Chat targets",
                "field_type": "multiselect",
                "options": ("agent-1", "agent-2"),
            },
        },
        state={},
        view_id="discuss.discussion.view",
    )

    control.controls[1].on_change(Mock(control=Mock(value=True)))

    assert intents == [{"__view_id": "discuss.discussion.view", "__state_update": {"participant_selection": ["agent-1"]}}]


def test_agent_loop_renderer_supports_terminal_checklist_progress_and_tabs() -> None:
    root = ViewRenderer(lambda _intent: None).render(
        {
            "component_type": "tabs",
            "properties": {"tabs": ("Current Task", "History")},
            "children": [
                {
                    "component_type": "panel",
                    "children": [
                        {"component_type": "terminal", "properties": {"binding_source": "current_task", "binding_path": "output"}},
                        {"component_type": "checklist", "properties": {"binding_source": "current_task", "binding_path": "checklist"}},
                        {"component_type": "progress", "properties": {"binding_source": "current_task", "binding_path": "progress"}},
                    ],
                },
                {"component_type": "text", "properties": {"content": "History"}},
            ],
        },
        data_sources={
            "current_task": {
                "status": "running",
                "checklist": [{"label": "Review", "done": True}],
                "events": [{"type": "task_started", "payload": {"title": "Test"}}],
            }
        },
        state={"selected_tab": "Current Task"},
        view_id="agent_loops.loops.view",
    )

    assert len(root.controls) == 2
    assert root.controls[1].content.controls[0].content.value.startswith("01 TASK STARTED")


def test_agent_loop_navigation_emits_contact_state_update() -> None:
    intents: list[dict[str, object]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "navigation",
            "properties": {"binding_source": "contacts", "binding_path": "items"},
        },
        data_sources={"contacts": {"items": [{"id": "agent:7", "title": "Karen", "task_count": 1}]}},
        state={},
        view_id="agent_loops.loops.view",
    )

    root.controls[0].on_click(None)

    assert intents == [{"__view_id": "agent_loops.loops.view", "__state_update": {"selected_contact_id": "agent:7"}}]


def test_generic_form_maps_schema_component_ids_to_api_field_names() -> None:
    intents: list[dict[str, object]] = []
    root = ViewRenderer(intents.append).render(
        {
            "component_type": "form",
            "action_keys": ("create",),
            "children": [
                {"component_type": "field", "component_id": "user-username-field", "properties": {"label": "Username"}},
                {"component_type": "field", "component_id": "user-is-enabled-field", "properties": {"label": "Enabled", "field_type": "checkbox"}},
            ],
        },
        actions={"create": {"key": "create", "label": "Create", "command_id": "users.create"}},
        view_id="users.users.view",
    )

    root.content.controls[0].value = "nick"
    root.content.controls[1].value = True
    root.content.controls[2].on_click(None)

    assert intents[0]["username"] == "nick"
    assert intents[0]["is_enabled"] is True


def test_markdown_expander_and_in_visibility_are_supported() -> None:
    root = ViewRenderer(lambda _intent: None).render(
        {
            "component_type": "expander",
            "properties": {"title": "Details"},
            "children": [{"component_type": "markdown", "properties": {"content": "**Ready**"}}],
            "visible_when": {"operator": "in", "operands": ["running", ["queued", "running"]]},
        },
        state={},
        view_id="example.view",
    )

    assert root.title.value == "Details"
    assert root.controls[0].value == "**Ready**"
