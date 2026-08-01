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

    def get_version(self) -> str:
        """Return the Core version used as the startup connectivity probe."""
        payload = self._request("GET", "/version")
        version = payload.get("version")
        if version is None:
            raise ApiConnectionError("Apmatia Core returned no version.")
        return str(version)
