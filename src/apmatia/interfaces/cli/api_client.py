from __future__ import annotations

import json
import os
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SESSION_COOKIE = "apmatia_session"


class CliApiError(RuntimeError):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _session_path() -> Path:
    override = os.getenv("APMATIA_CLI_SESSION_FILE")
    if override:
        return Path(override).expanduser()
    config_dir = Path(os.getenv("APMATIA_CONFIG_DIR", str(Path.home() / ".config" / "apmatia"))).expanduser()
    return config_dir / "cli-session.json"


def _load_token() -> str | None:
    try:
        payload = json.loads(_session_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    token = payload.get("token") if isinstance(payload, dict) else None
    return str(token) if token else None


def _save_token(token: str | None) -> None:
    path = _session_path()
    if not token:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": token}), encoding="utf-8")
    path.chmod(0o600)


def _request(method: str, path: str, *, json_payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
    base_url = os.getenv("APMATIA_API_URL", "http://127.0.0.1:8000/api").rstrip("/")
    query = urlencode({key: value for key, value in (params or {}).items() if value is not None})
    url = f"{base_url}{path}" + (f"?{query}" if query else "")
    headers = {"Accept": "application/json"}
    token = _load_token()
    if token:
        headers["Cookie"] = f"{SESSION_COOKIE}={token}"
    data = None
    if json_payload is not None:
        data = json.dumps(json_payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=float(os.getenv("APMATIA_CLI_TIMEOUT", "15"))) as response:
            body = response.read()
            _capture_session_cookie(response.headers.get("Set-Cookie"), clear=path == "/auth/logout")
            return json.loads(body) if body else None
    except HTTPError as error:
        body = error.read()
        try:
            payload = json.loads(body) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        detail = payload.get("detail", error.reason) if isinstance(payload, dict) else error.reason
        raise CliApiError(str(detail), error.code) from error
    except (URLError, TimeoutError, OSError) as error:
        raise CliApiError(f"Unable to reach Apmatia API at {base_url}: {error}", 503) from error


def _capture_session_cookie(header: str | None, *, clear: bool = False) -> None:
    if clear:
        _save_token(None)
        return
    if not header:
        return
    cookies = SimpleCookie()
    cookies.load(header)
    morsel = cookies.get(SESSION_COOKIE)
    if morsel is not None and morsel.value:
        _save_token(morsel.value)


def list_module_commands() -> list[dict[str, Any]]:
    payload = _request("GET", "/module-commands")
    return list(payload or [])


def execute_module_command(command_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = _request("POST", f"/module-commands/{command_id}", json_payload={"payload": payload})
    return dict(result or {})


def login(username: str, password: str) -> dict[str, Any]:
    return dict(_request("POST", "/auth/login", json_payload={"username": username, "password": password}) or {})


def register(username: str, password: str) -> dict[str, Any]:
    return dict(_request("POST", "/auth/register", json_payload={"username": username, "password": password}) or {})


def logout() -> dict[str, Any]:
    return dict(_request("POST", "/auth/logout") or {})


def session() -> dict[str, Any]:
    return dict(_request("GET", "/auth/session") or {})


def prompt(prompt_text: str, output_dir: str | None = None) -> str:
    payload = _request("GET", "/prompt", params={"prompt": prompt_text, "output_dir": output_dir})
    return str((payload or {}).get("message") or "")
