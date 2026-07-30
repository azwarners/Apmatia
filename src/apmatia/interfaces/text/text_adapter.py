"""Deliberately small second GUI adapter using only HTTP/document APIs.

This adapter proves the API/document boundary is framework-neutral. It covers authentication,
generic CRUD/form views, dynamic options, one management view, Discussion timeline/composer
behavior, Agent Loops polling/terminal behavior, navigation, confirmations, and action-result
effects. Visual parity with Streamlit is not required; semantic operation is.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextAdapterSession:
    """Session state for the text adapter."""

    authenticated_user: dict[str, Any] | None = None
    auth_token: str | None = None
    route: str = "login"
    selected_module_id: str | None = None
    selected_view_id: str | None = None
    notifications: list[str] = field(default_factory=list)


class TextAdapter:
    """A minimal text-based GUI adapter for proving contract replaceability."""

    def __init__(self, api_client: Any) -> None:
        """Initialize the adapter with an HTTP/document API client.

        Args:
            api_client: An object exposing the authenticated HTTP/document API operations.
        """
        self._api = api_client
        self.session = TextAdapterSession()

    # =========================================================================
    # Authentication
    # =========================================================================

    def login(self, username: str, password: str) -> bool:
        """Log in with username and password.

        Args:
            username: The username to authenticate.
            password: The password to authenticate.

        Returns:
            True if login succeeded, False otherwise.
        """
        try:
            response = self._api.login(username, password)
            self.session.authenticated_user = response.get("user")
            self.session.auth_token = response.get("token")
            self.session.route = "module_view"
            self._notify(f"Welcome back, {username}!")
            return True
        except Exception as e:
            self._notify(f"Login failed: {e}")
            return False

    def register(self, username: str, password: str, password_confirm: str) -> bool:
        """Register a new user.

        Args:
            username: The username to register.
            password: The password to register.
            password_confirm: The password confirmation.

        Returns:
            True if registration succeeded, False otherwise.
        """
        if password != password_confirm:
            self._notify("Passwords do not match.")
            return False

        try:
            response = self._api.register(username, password)
            self.session.authenticated_user = response.get("user")
            self.session.auth_token = response.get("token")
            self.session.route = "module_view"
            self._notify(f"Welcome, {username}!")
            return True
        except Exception as e:
            self._notify(f"Registration failed: {e}")
            return False

    def logout(self) -> None:
        """Log out the current user."""
        self.session.authenticated_user = None
        self.session.auth_token = None
        self.session.route = "login"
        self._notify("Logged out.")

    # =========================================================================
    # Generic CRUD/Form Views
    # =========================================================================

    def render_collection_view(self, view_document: dict[str, Any]) -> str:
        """Render a collection view document.

        Args:
            view_document: The serialized view document.

        Returns:
            A text representation of the collection.
        """
        lines = [f"=== {view_document.get('title', 'Collection')} ==="]

        # Render columns as headers
        columns = view_document.get("columns", [])
        if columns:
            header = " | ".join(col.get("label", col.get("key", "?")) for col in columns)
            lines.append(header)
            lines.append("-" * len(header))

        # Render items
        items = view_document.get("items", [])
        for item in items:
            row = " | ".join(str(item.get(col.get("key", "id"), "-")) for col in columns)
            lines.append(row)

        # Render actions
        actions = view_document.get("item_actions", [])
        if actions:
            lines.append("")
            lines.append("Item actions:")
            for action in actions:
                lines.append(f"  - {action.get('label', action.get('key', '?'))}")

        return "\n".join(lines)

    def render_form_view(self, view_document: dict[str, Any]) -> str:
        """Render a form view document.

        Args:
            view_document: The serialized view document.

        Returns:
            A text representation of the form.
        """
        lines = [f"=== {view_document.get('title', 'Form')} ==="]

        fields = view_document.get("fields", [])
        for field_def in fields:
            label = field_def.get("label", field_def.get("key", "?"))
            field_type = field_def.get("field_type", "text")
            default = field_def.get("default", "")
            required = field_def.get("required", False)
            req_mark = "*" if required else ""
            lines.append(f"{label}{req_mark} [{field_type}]: {default}")

        actions = view_document.get("actions", [])
        if actions:
            lines.append("")
            lines.append("Actions:")
            for action in actions:
                lines.append(f"  - {action.get('label', action.get('key', '?'))}")

        return "\n".join(lines)

    # =========================================================================
    # Dynamic Options
    # =========================================================================

    def resolve_dynamic_options(self, source_key: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        """Resolve dynamic option sources.

        Args:
            source_key: The data source key to resolve.
            parameters: Parameters for the operation.

        Returns:
            A list of option dictionaries with 'id' and 'label' keys.
        """
        try:
            result = self._api.resolve_data_source(source_key, parameters)
            items = result.get("items", [])
            return [{"id": item.get("id"), "label": item.get("label", str(item.get("id")))} for item in items]
        except Exception as e:
            return [{"id": None, "label": f"Error: {e}"}]

    # =========================================================================
    # Management View (Agent Config example)
    # =========================================================================

    def render_agent_config_view(self, agent_id: str) -> str:
        """Render an agent configuration view.

        Args:
            agent_id: The agent ID to configure.

        Returns:
            A text representation of the agent config.
        """
        try:
            agent = self._api.get_agent(agent_id)
            lines = [f"=== Agent: {agent.get('name', agent_id)} ==="]
            lines.append(f"ID: {agent.get('id')}")
            lines.append(f"Owner: {agent.get('owner_user_id')}")

            model = agent.get("model_config", {})
            if model:
                lines.append(f"Model: {model.get('model_id')} ({model.get('backend')})")

            return "\n".join(lines)
        except Exception as e:
            return f"Agent config error: {e}"

    # =========================================================================
    # Discussion Timeline/Composer
    # =========================================================================

    def render_discussion_timeline(self, discussion_id: str) -> str:
        """Render a discussion timeline.

        Args:
            discussion_id: The discussion ID to render.

        Returns:
            A text representation of the discussion timeline.
        """
        try:
            tree = self._api.discussion_tree()
            discussions = tree.get("discussions", [])
            discussion = next((d for d in discussions if str(d.get("discussion_id")) == str(discussion_id)), None)

            if not discussion:
                return f"Discussion {discussion_id} not found."

            lines = [f"=== Discussion: {discussion.get('title', 'Untitled')} ==="]

            messages = discussion.get("messages", [])
            for msg in messages:
                speaker = msg.get("speaker_name", "?")
                text = msg.get("text", "")
                lines.append(f"[{speaker}] {text}")

            return "\n".join(lines)
        except Exception as e:
            return f"Discussion timeline error: {e}"

    def send_discussion_message(self, discussion_id: str, text: str) -> dict[str, Any]:
        """Send a message to a discussion.

        Args:
            discussion_id: The discussion ID to send to.
            text: The message text.

        Returns:
            A result dictionary with status and any new messages.
        """
        try:
            result = self._api.prompt_discussion(discussion_id, text)
            self._notify("Message sent.")
            return {"status": "success", "result": result}
        except Exception as e:
            self._notify(f"Message failed: {e}")
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # Agent Loops Polling/Terminal
    # =========================================================================

    def start_agent_loop_task(self, agent_id: str, task_description: str) -> str:
        """Start an Agent Loops task.

        Args:
            agent_id: The agent ID to run the task.
            task_description: The task description.

        Returns:
            The task ID for polling.
        """
        try:
            result = self._api.start_agent_loop_task(agent_id, task_description)
            task_id = result.get("task_id")
            self._notify(f"Task started: {task_id}")
            return str(task_id)
        except Exception as e:
            self._notify(f"Task start failed: {e}")
            return ""

    def poll_agent_loop_task(self, task_id: str) -> dict[str, Any]:
        """Poll an Agent Loops task for progress.

        Args:
            task_id: The task ID to poll.

        Returns:
            A dictionary with task status, output, and completion state.
        """
        try:
            result = self._api.poll_agent_loop_task(task_id)
            return {
                "status": result.get("status", "unknown"),
                "output": result.get("output", []),
                "complete": result.get("complete", False),
                "error": result.get("error"),
            }
        except Exception as e:
            return {"status": "error", "output": [], "complete": False, "error": str(e)}

    def stop_agent_loop_task(self, task_id: str) -> bool:
        """Stop an Agent Loops task.

        Args:
            task_id: The task ID to stop.

        Returns:
            True if the task was stopped, False otherwise.
        """
        try:
            self._api.stop_agent_loop_task(task_id)
            self._notify(f"Task {task_id} stopped.")
            return True
        except Exception as e:
            self._notify(f"Task stop failed: {e}")
            return False

    # =========================================================================
    # Navigation
    # =========================================================================

    def navigate_to_view(self, module_id: str, view_id: str) -> None:
        """Navigate to a specific module view.

        Args:
            module_id: The module ID to navigate to.
            view_id: The view ID within the module.
        """
        self.session.selected_module_id = module_id
        self.session.selected_view_id = view_id
        self.session.route = "module_view"
        self._notify(f"Navigated to {module_id}.{view_id}")

    def navigate_back(self) -> None:
        """Navigate back to the previous view."""
        self.session.route = "login"
        self._notify("Navigated back to login.")

    # =========================================================================
    # Confirmations
    # =========================================================================

    def confirm_action(self, action_label: str, confirmation_message: str) -> bool:
        """Confirm an action.

        Args:
            action_label: The action label.
            confirmation_message: The confirmation message.

        Returns:
            True if confirmed, False otherwise.
        """
        # In a real adapter, this would wait for user input
        print(f"Confirm: {confirmation_message}")
        return True

    # =========================================================================
    # Action-Result Effects
    # =========================================================================

    def apply_effect(self, effect: dict[str, Any]) -> None:
        """Apply an effect from an action result.

        Args:
            effect: The effect dictionary with effect_type and target/value.
        """
        effect_type = effect.get("effect_type")
        target = effect.get("target")

        if effect_type == "refresh_view":
            self._notify(f"Refreshing view: {target}")
        elif effect_type == "navigate":
            self.session.route = target
            self._notify(f"Navigating to: {target}")
        elif effect_type == "show_notification":
            self._notify(effect.get("value", "Notification"))
        elif effect_type == "set_state":
            # In a real adapter, this would update session state
            pass

    # =========================================================================
    # Utilities
    # =========================================================================

    def _notify(self, message: str) -> None:
        """Add a notification to the session.

        Args:
            message: The notification message.
        """
        self.session.notifications.append(message)
        # In a real adapter, this would print or display the notification
        print(f"[NOTIFY] {message}")

    def get_notifications(self) -> list[str]:
        """Get and clear notifications.

        Returns:
            A list of notification messages.
        """
        notifications = self.session.notifications
        self.session.notifications = []
        return notifications

    def is_authenticated(self) -> bool:
        """Check if the user is authenticated.

        Returns:
            True if authenticated, False otherwise.
        """
        return self.session.authenticated_user is not None

    def get_current_route(self) -> str:
        """Get the current route.

        Returns:
            The current route string.
        """
        return self.session.route