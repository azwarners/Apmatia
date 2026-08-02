"""HTTP client for Apmatia Core API."""

from __future__ import annotations

import os
from typing import Any

import requests

from .errors import ApiConnectionError, AuthenticationError


class ApmatiaApiClient:
    """HTTP client for Apmatia Core API."""

    def __init__(self, base_url: str | None = None):
        configured_url = base_url or os.environ.get("APMATIA_API_URL", "http://127.0.0.1:8000/api")
        self.base_url = configured_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, json=json, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError as error:
            raise ApiConnectionError(f"Cannot connect to Apmatia API at {self.base_url}") from error
        except requests.HTTPError as error:
            if error.response.status_code == 401:
                detail = "Invalid credentials"
                try:
                    detail = str(error.response.json().get("detail") or detail)
                except (ValueError, AttributeError):
                    pass
                raise AuthenticationError(detail) from error
            detail = f"API error: {error}"
            try:
                detail = str(error.response.json().get("detail") or detail)
            except (ValueError, AttributeError):
                pass
            raise ApiConnectionError(detail) from error

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/auth/login", json={"username": username, "password": password})

    def get_session(self) -> dict[str, Any]:
        return self._request("GET", "/auth/session")

    def logout(self) -> dict[str, Any]:
        return self._request("POST", "/auth/logout")

    def get_auth_views(self) -> list[dict[str, Any]]:
        return self._request("GET", "/auth/views")

    def list_modules(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/modules")
        if not isinstance(payload, list):
            raise ApiConnectionError("Apmatia Core returned an invalid module catalog.")
        return payload

    def get_module_view_document(self, view_id: str) -> dict[str, Any]:
        payload = self._request("GET", f"/module-views/{view_id}/document")
        if not isinstance(payload, dict):
            raise ApiConnectionError("Apmatia Core returned an invalid view document.")
        return payload

    def list_module_view_items(self, view_id: str) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/module-views/{view_id}/items")
        if not isinstance(payload, list):
            raise ApiConnectionError("Apmatia Core returned invalid view items.")
        return payload

    def execute_module_command(self, command_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._request("POST", f"/module-commands/{command_id}", json={"payload": payload})
        if not isinstance(result, dict):
            raise ApiConnectionError("Apmatia Core returned an invalid command result.")
        return result

    def load_view_source(self, operation: str, parameters: dict[str, Any] | None = None) -> Any:
        return self._request("POST", f"/module-view-sources/{operation}", json={"parameters": parameters or {}})

    def send_discussion_prompt(self, prompt: str, *, agent_id: Any = None, discussion_id: Any = None, model_id: Any = None) -> dict[str, Any]:
        result = self._request(
            "POST",
            "/discussion/prompt",
            json={"prompt": prompt, "agent_id": agent_id, "discussion_id": discussion_id, "model_id": model_id},
        )
        if not isinstance(result, dict):
            raise ApiConnectionError("Apmatia Core returned an invalid discussion response.")
        return result

    def get_version(self) -> str:
        """Return the Core version used as the startup connectivity probe."""
        payload = self._request("GET", "/version")
        version = payload.get("version")
        if version is None:
            raise ApiConnectionError("Apmatia Core returned no version.")
        return str(version)
