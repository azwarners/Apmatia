"""HTTP client for Apmatia Core API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from .errors import ApiConnectionError, AuthenticationError


AUTH_SESSION_COOKIE_NAME = "apmatia_session"


def _session_path() -> Path:
    """Return the file used to persist the Flet client's session cookie."""
    override = os.environ.get("APMATIA_FLET_SESSION_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "apmatia" / "flet-session.json"


class ApmatiaApiClient:
    """HTTP client for Apmatia Core API."""

    def __init__(self, base_url: str | None = None):
        configured_url = base_url or os.environ.get("APMATIA_API_URL", "http://127.0.0.1:8000/api")
        self.base_url = configured_url.rstrip("/")
        self.session = requests.Session()
        self._restore_session_cookie()

    @staticmethod
    def _load_persisted_cookie() -> str | None:
        try:
            payload = json.loads(_session_path().read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        token = payload.get("token") if isinstance(payload, dict) else None
        return str(token) if token else None

    def _restore_session_cookie(self) -> None:
        token = self._load_persisted_cookie()
        if token:
            self.session.cookies.set(AUTH_SESSION_COOKIE_NAME, token)

    @staticmethod
    def _save_persisted_cookie(token: str | None) -> None:
        path = _session_path()
        if not token:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        temporary_path.write_text(json.dumps({"token": token}), encoding="utf-8")
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
        path.chmod(0o600)

    def _persist_current_cookie(self, *, clear: bool = False) -> None:
        if clear:
            self._save_persisted_cookie(None)
            return
        token = next(
            (cookie.value for cookie in self.session.cookies if cookie.name == AUTH_SESSION_COOKIE_NAME),
            None,
        )
        self._save_persisted_cookie(token)

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, json=json, timeout=30)
            response.raise_for_status()
            self._persist_current_cookie(clear=path == "/auth/logout")
            return response.json()
        except requests.ConnectionError as error:
            raise ApiConnectionError(f"Cannot connect to Apmatia API at {self.base_url}") from error
        except requests.HTTPError as error:
            if error.response.status_code == 401:
                self._persist_current_cookie(clear=True)
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
