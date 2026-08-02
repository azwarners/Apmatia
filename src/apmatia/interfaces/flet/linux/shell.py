"""Linux desktop shell for the first Flet authentication vertical slice."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import flet as ft

from ..common.api_client import ApmatiaApiClient
from ..common.errors import AdapterError, ApiConnectionError, AuthenticationError, UnsupportedComponentError
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
        self._sidebar_width = 260
        self._sidebar_control: ft.Container | None = None
        self._current_content: ft.Control = ft.Container()
        self._current_title = "Apmatia"
        self._view_state: dict[str, Any] = {}
        self._loop_poll_task: Any = None
        self._login_document: dict[str, Any] | None = None
        self._modules: list[dict[str, Any]] | None = None
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
        if not (self._page.route.startswith("/view/agent_loops.loops.view") and self._view_state.get("is_running")):
            self._cancel_loop_polling()
        if self._page.route != "/login" and not self._state.is_authenticated:
            self._page.route = "/login"
        if self._page.route == "/login":
            self._render_login()
        elif self._page.route.startswith("/view/"):
            self._render_module_view(self._page.route.removeprefix("/view/"))
        else:
            self._render_workspace()
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

    def _render_workspace(self) -> None:
        """Render the authenticated Linux shell and generic module catalog."""
        try:
            self._ensure_module_catalog()
        except AuthenticationError:
            self._state.clear_authentication()
            self._page.route = "/login"
            self._render_login()
            return
        except ApiConnectionError as error:
            self._render_shell(self._message_view("Unable to load modules", str(error), self._retry_catalog))
            return

        modules = self._visible_modules()
        if not modules:
            content = self._message_view("No modules available", "Apmatia Core returned an empty module catalog.")
        else:
            content = self._message_view(
                "Apmatia Linux Client",
                "Select a module view from the navigation rail to begin.",
            )
        self._render_shell(content)

    def _render_module_view(self, view_id: str) -> None:
        """Resolve and render one portable view document from Core."""
        if not view_id:
            self._page.route = "/"
            self._render_workspace()
            return
        try:
            self._ensure_module_catalog()
            document = self._api.get_module_view_document(view_id)
            declared_sources = document.get("data_sources", [])
            data_sources: dict[str, Any] = {}
            for source in declared_sources:
                source_key = str(source.get("key") or "")
                operation = str(source.get("operation") or "")
                if not source_key or not operation:
                    continue
                try:
                    data_sources[source_key] = self._api.load_view_source(
                        operation,
                        {
                            "discussion_id": self._view_state.get("selected_discussion_id"),
                            "task_id": self._view_state.get("selected_task_id"),
                            "contact_id": self._view_state.get("selected_contact_id"),
                        },
                    )
                except AdapterError:
                    data_sources[source_key] = []
            actions = {str(action.get("key")): action for action in document.get("actions", [])}
        except AuthenticationError:
            self._state.clear_authentication()
            self._page.route = "/login"
            self._render_login()
            return
        except ApiConnectionError as error:
            self._render_shell(self._message_view("View unavailable", str(error)))
            return
        try:
            rendered = self._renderer.render(
                document["presentation"],
                actions=actions,
                data_sources=data_sources,
                state=self._view_state,
                view_id=view_id,
            )
        except (KeyError, UnsupportedComponentError) as error:
            rendered = self._message_view(
                str(document.get("title") or view_id),
                f"This portable view needs a Phase 3 renderer component: {error}",
            )
        self._render_shell(rendered, title=str(document.get("title") or view_id))
        if view_id == "agent_loops.loops.view" and self._view_state.get("is_running"):
            self._ensure_loop_polling()

    def _ensure_loop_polling(self) -> None:
        if self._loop_poll_task is None or self._loop_poll_task.done():
            self._loop_poll_task = self._page.run_task(self._poll_agent_loop)

    def _cancel_loop_polling(self) -> None:
        if self._loop_poll_task is not None and not self._loop_poll_task.done():
            self._loop_poll_task.cancel()
        self._loop_poll_task = None

    async def _poll_agent_loop(self) -> None:
        while self._page.route.startswith("/view/agent_loops.loops.view") and self._view_state.get("is_running"):
            await asyncio.sleep(1.0)
            if self._page.route.startswith("/view/agent_loops.loops.view") and self._view_state.get("is_running"):
                self.render_route()

    def _ensure_module_catalog(self) -> None:
        if self._modules is None:
            catalog = self._api.list_modules()
            self._modules = catalog if isinstance(catalog, list) else []

    def _retry_catalog(self, event: ft.ControlEvent | None = None) -> None:
        del event
        self._modules = None
        self.render_route()

    def _visible_modules(self) -> list[dict[str, Any]]:
        visible: list[dict[str, Any]] = []
        for module in self._modules or []:
            if module.get("hidden"):
                continue
            views = [
                view
                for view in module.get("views", [])
                if not view.get("effective_hidden")
                and (view.get("metadata") or {}).get("ui", {}).get("navigation") != "pre_authentication"
            ]
            if views or not module.get("views"):
                visible.append({**module, "views": views})
        return visible

    def _render_shell(self, content: ft.Control, *, title: str = "Apmatia") -> None:
        self._content.content = ft.Row(
            controls=[
                self._navigation_rail(),
                ft.GestureDetector(
                    content=ft.Container(width=8, expand=True, bgcolor=ft.Colors.OUTLINE_VARIANT),
                    mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
                    on_pan_update=self._resize_sidebar,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                                    ft.Container(expand=True),
                                    ft.Text(self._state.username or ""),
                                    ft.Button("Log out", on_click=self._handle_logout),
                                ],
                            ),
                            ft.Divider(),
                            content,
                        ],
                        expand=True,
                    ),
                    padding=ft.Padding(24, 24, 24, 24),
                    expand=True,
                ),
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self._page.controls.clear()
        self._page.add(self._content)
        self._current_content = content
        self._current_title = title

    def _navigation_rail(self) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text("Modules", size=18, weight=ft.FontWeight.BOLD),
            ft.Button("Home", on_click=lambda _event: self._navigate("/")),
        ]
        for module in self._visible_modules():
            module_name = str(module.get("name") or module.get("module_id") or "Unnamed module")
            controls.append(ft.Text(module_name, weight=ft.FontWeight.BOLD))
            for view in module.get("views", []):
                view_id = str(view.get("view_id") or "")
                view_name = str(view.get("name") or view_id or "Unnamed view")
                controls.append(
                    ft.Button(view_name, on_click=lambda _event, view_id=view_id: self._navigate(f"/view/{view_id}"))
                )
        self._sidebar_control = ft.Container(
            content=ft.Column(controls=controls, scroll=ft.ScrollMode.AUTO, spacing=8),
            width=self._sidebar_width,
            padding=ft.Padding(16, 16, 16, 16),
        )
        return self._sidebar_control

    def _resize_sidebar(self, event: ft.DragUpdateEvent) -> None:
        """Resize the desktop navigation rail within usable bounds."""
        local_delta = getattr(event, "local_delta", None)
        delta_x = getattr(local_delta, "x", None) if local_delta is not None else None
        if not isinstance(delta_x, (int, float)):
            delta_x = getattr(event, "delta_x", 0)
        delta_x = float(delta_x or 0)
        self._sidebar_width = max(200, min(480, self._sidebar_width + delta_x))
        if self._sidebar_control is not None:
            self._sidebar_control.width = self._sidebar_width
            self._page.update()


    def _navigate(self, route: str) -> None:
        self._page.route = route
        self.render_route()

    @staticmethod
    def _message_view(title: str, message: str, retry: Any | None = None) -> ft.Control:
        controls: list[ft.Control] = [ft.Text(title, size=28, weight=ft.FontWeight.BOLD), ft.Text(message)]
        if retry is not None:
            controls.append(ft.Button("Retry", on_click=retry))
        return ft.Container(
            content=ft.Column(
                controls=controls,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            expand=True,
        )

    def _handle_intent(self, payload: dict[str, Any]) -> None:
        logger.info("Received client intent %s", payload.get("auth_action") or payload.get("__action_key") or "unknown")
        if payload.get("auth_action") == "login" or {"username", "password"}.issubset(payload):
            self._handle_login(payload)
        elif payload.get("__view_id"):
            self._handle_module_intent(payload)
        else:
            logger.warning(
                "Ignoring unsupported client intent %r",
                payload.get("auth_action", "unknown"),
            )

    def _handle_module_intent(self, payload: dict[str, Any]) -> None:
        if payload.get("__state_update"):
            self._view_state.update(payload["__state_update"])
            self.render_route()
            return
        action_key = str(payload.pop("__action_key", ""))
        payload.pop("__view_id", None)
        if action_key == "create":
            self._view_state.update({"show_create_form": True, "show_edit_form": False, "edit_item": None})
            self.render_route()
            return
        if action_key == "edit":
            self._view_state.update({"show_create_form": False, "show_edit_form": True, "edit_item": payload.get("item")})
            self.render_route()
            return
        api_operation = str(payload.pop("api_operation", "") or "")
        if api_operation == "discussion_prompt":
            prompt = str(payload.pop("prompt", "") or "").strip()
            if not prompt:
                self._show_error("Please enter a message before sending.")
                return
            try:
                self._api.send_discussion_prompt(
                    prompt,
                    agent_id=payload.pop("agent_id", None),
                    discussion_id=payload.pop("discussion_id", None),
                    model_id=payload.pop("model_id", None),
                )
            except AdapterError as error:
                self._show_error(str(error))
                return
            self._view_state["message_input"] = ""
            self.render_route()
            return
        command_id = str(payload.pop("command_id", "") or "")
        if not command_id:
            self._show_error(f"The {action_key or 'requested'} action is not connected to a Core command.")
            return
        try:
            result = self._api.execute_module_command(command_id, payload)
        except AdapterError as error:
            self._show_error(str(error))
            return
        if command_id == "agent_loops.start":
            task_id = result.get("task_id") if isinstance(result, dict) else None
            if task_id:
                self._view_state["selected_task_id"] = task_id
            self._view_state["is_running"] = True
        elif command_id == "agent_loops.stop":
            self._view_state["is_running"] = False
        self.render_route()

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
        controls: list[ft.Control] = [ft.Text("Apmatia", size=36, weight=ft.FontWeight.BOLD), ft.Text(message, color=ft.Colors.RED)]
        if self._state.is_authenticated and self._page.route != "/login":
            controls.append(ft.Button("Retry", on_click=self._retry_current_route))
        self._content.content = ft.Column(
            controls=controls,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self._page.controls.clear()
        self._page.add(self._content)
        self._page.update()

    def _retry_current_route(self, event: ft.ControlEvent | None = None) -> None:
        del event
        self.render_route()

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
