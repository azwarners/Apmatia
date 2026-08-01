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
    assert page.controls[0].content.controls[1].content.controls[1].value == "Signed in as testuser"


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
