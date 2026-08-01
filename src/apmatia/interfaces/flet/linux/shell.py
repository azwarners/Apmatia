"""Linux desktop shell for the first Flet authentication vertical slice."""

from __future__ import annotations

import logging
from typing import Any

import flet as ft

from ..common.api_client import ApmatiaApiClient
from ..common.errors import AdapterError, ApiConnectionError, AuthenticationError
from ..common.renderer import ViewRenderer
from ..common.state import ClientState

logger = logging.getLogger("apmatia.flet.linux")


class ApmatiaShell:
    """Resolve authentication state and render the portable login view."""

    def __init__(
        self,
        page: ft.Page,
        api_client: ApmatiaApiClient | None = None,
        core_version: str | None = None,
    ):
        self._page = page
        self._api = api_client or ApmatiaApiClient()
        self._core_version = core_version or "unknown"
        self._state = ClientState(page)
        self._content = ft.Container(expand=True)
        self._login_document: dict[str, Any] | None = None
        self._renderer = ViewRenderer(self._handle_intent)

    @property
    def container(self) -> ft.Container:
        return self._content

    def start(self) -> None:
        """Resolve the server session before selecting the initial route."""
        try:
            session = self._api.get_session()
        except AdapterError as error:
            self._show_error(str(error))
            return
        if session.get("authenticated"):
            self._state.set_authenticated(session)
            self._page.route = "/"
        else:
            self._state.clear_authentication()
            self._page.route = "/login"
        self.render_route()

    def on_route_change(self, event: ft.RouteChangeEvent | None = None) -> None:
        del event
        self.render_route()

    def render_route(self) -> None:
        """Render the current route, enforcing protection before rendering."""
        if self._page.route != "/login" and not self._state.is_authenticated:
            self._page.route = "/login"
        if self._page.route == "/login":
            self._render_login()
        else:
            self._render_protected_placeholder()
        self._page.update()

    def _render_login(self) -> None:
        try:
            views = self._api.get_auth_views()
            self._login_document = next(view for view in views if view.get("view_id") == "auth.login.view")
            content = self._renderer.render(self._login_presentation(self._login_document))
        except (AdapterError, StopIteration) as error:
            self._show_error(f"Unable to load the Apmatia login view: {error}")
            return
        self._content.content = ft.Column(
            controls=[
                ft.Text(f"Connected to Apmatia Core (version {self._core_version})", color=ft.Colors.GREEN),
                ft.Container(content=content, alignment=ft.Alignment.CENTER, expand=True),
            ],
            expand=True,
        )
        self._page.controls.clear()
        self._page.add(self._content)

    @staticmethod
    def _login_presentation(document: dict[str, Any]) -> dict[str, Any]:
        """Attach the document action payload to the form's rendered action."""
        actions = {action.get("key"): action for action in document.get("actions", [])}

        def visit(component: dict[str, Any]) -> dict[str, Any]:
            result = dict(component)
            properties = dict(result.get("properties") or {})
            if result.get("component_type") == "form":
                form_actions = []
                declared_actions = properties.get("actions") or []
                if not declared_actions and properties.get("submit_label"):
                    declared_actions = [{"key": "login", "label": properties["submit_label"]}]
                for action in declared_actions:
                    form_action = dict(action)
                    source = actions.get(form_action.get("key"), {})
                    form_action["payload"] = dict(source.get("payload") or {})
                    if document.get("view_id") == "auth.login.view":
                        form_action["payload"].setdefault("auth_action", "login")
                    form_actions.append(form_action)
                properties["actions"] = form_actions
            result["properties"] = properties
            result["children"] = [visit(child) for child in result.get("children", [])]
            return result

        return visit(document["presentation"])

    def _render_protected_placeholder(self) -> None:
        username = self._state.username or "unknown user"
        self._content.content = ft.Column(
            controls=[
                ft.AppBar(
                    title=ft.Text("Apmatia"),
                    actions=[ft.Button("Log out", on_click=self._handle_logout)],
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Linux Client", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Signed in as {username}"),
                            ft.Text("Connected to Apmatia Core."),
                            ft.Text("The Phase 2 Linux authentication slice succeeded."),
                        ],
                        spacing=12,
                    ),
                    padding=ft.Padding(32, 32, 32, 32),
                ),
            ],
            expand=True,
        )
        self._page.controls.clear()
        self._page.add(self._content)

    def _handle_intent(self, payload: dict[str, Any]) -> None:
        logger.info("Received client intent %s", payload.get("auth_action", "unknown"))
        if payload.get("auth_action") == "login" or {"username", "password"}.issubset(payload):
            self._handle_login(payload)
        else:
            logger.warning(
                "Ignoring unsupported client intent %r",
                payload.get("auth_action", "unknown"),
            )

    def _handle_login(self, payload: dict[str, Any]) -> None:
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not username or not password:
            self._show_error("Please enter both username and password.")
            return
        logger.info("Submitting login for user %s", username)
        self._show_status("Signing in to Apmatia Core...")
        try:
            self._api.login(username, password)
            session = self._api.get_session()
            if not session.get("authenticated"):
                self._show_error("Login failed. Please check your credentials.")
                return
        except AuthenticationError as error:
            logger.info("Login rejected for user %s: %s", username, error)
            self._show_error(str(error))
            return
        except ApiConnectionError as error:
            logger.warning("Login request failed for user %s: %s", username, error)
            self._show_error(str(error))
            return
        self._state.set_authenticated(session)
        self._page.route = "/"
        self.render_route()

    def _handle_logout(self, event: ft.ControlEvent | None = None) -> None:
        del event
        try:
            self._api.logout()
        except AdapterError:
            pass
        self._state.clear_authentication()
        self._page.route = "/login"
        self.render_route()

    def _show_error(self, message: str) -> None:
        self._content.content = ft.Column(
            controls=[ft.Text("Apmatia", size=36, weight=ft.FontWeight.BOLD), ft.Text(message, color=ft.Colors.RED)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self._page.controls.clear()
        self._page.add(self._content)
        self._page.update()

    def _show_status(self, message: str) -> None:
        self._content.content = ft.Column(
            controls=[ft.ProgressRing(), ft.Text(message)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self._page.controls.clear()
        self._page.add(self._content)
        self._page.update()
