"""In-process API client for the Streamlit interface."""
from __future__ import annotations

import json
from collections.abc import Mapping
import sys
from typing import Any
from urllib.parse import urlencode
from types import SimpleNamespace

try:
    import streamlit as st
except ModuleNotFoundError:
    class _StreamlitProxy:
        def _resolve(self) -> Any:
            module = sys.modules.get("streamlit")
            if module is None:
                module = SimpleNamespace(session_state={}, html=lambda *args, **kwargs: None, context=None)
            return module

        def __getattr__(self, name: str) -> Any:
            return getattr(self._resolve(), name)

    st = _StreamlitProxy()

try:
    from fastapi.testclient import TestClient
    from apmatia.api.http.app import create_app
    from apmatia.api.http.routes.settings_routes import SettingsPayload
except ModuleNotFoundError as error:
    if error.name not in {"fastapi", "apmatia.api.http.app", "apmatia.api.http.routes.settings_routes"}:
        raise

    TestClient = None  # type: ignore[assignment]

    def create_app() -> None:
        raise ModuleNotFoundError("fastapi is required for the Streamlit API client.")

    class SettingsPayload(dict[str, Any]):
        pass

AUTH_SESSION_COOKIE_NAME = "apmatia_session"
AUTH_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


class ApiError(RuntimeError):
    """Raised when the local API returns an error response."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _cookie_state() -> dict[str, str]:
    cookies = st.session_state.get("api_cookies")
    if not isinstance(cookies, dict):
        cookies = {}
        st.session_state["api_cookies"] = cookies
    if AUTH_SESSION_COOKIE_NAME not in cookies:
        browser_cookie = _browser_cookie_value()
        if browser_cookie:
            cookies[AUTH_SESSION_COOKIE_NAME] = browser_cookie
    return cookies


def _browser_cookie_value() -> str | None:
    context = getattr(st, "context", None)
    if context is None:
        return None

    cookies = getattr(context, "cookies", None)
    if cookies is None:
        return None

    if isinstance(cookies, Mapping):
        value = cookies.get(AUTH_SESSION_COOKIE_NAME)
        return None if value in (None, "") else str(value)

    try:
        value = cookies.get(AUTH_SESSION_COOKIE_NAME)
    except AttributeError:
        return None
    return None if value in (None, "") else str(value)


def _sync_browser_cookie(token: str | None) -> None:
    if token:
        cookie_string = (
            f"{AUTH_SESSION_COOKIE_NAME}={token}; "
            f"max-age={AUTH_SESSION_COOKIE_MAX_AGE_SECONDS}; path=/; samesite=lax"
        )
    else:
        cookie_string = f"{AUTH_SESSION_COOKIE_NAME}=; max-age=0; path=/; samesite=lax"

    st.html(
        f"""
        <script>
        document.cookie = {json.dumps(cookie_string)};
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def _jar_session_cookie_value(cookie_jar: Any) -> str | None:
    jar = getattr(cookie_jar, "jar", None)
    if jar is None:
        if isinstance(cookie_jar, Mapping):
            value = cookie_jar.get(AUTH_SESSION_COOKIE_NAME)
            return None if value in (None, "") else str(value)
        try:
            value = cookie_jar.get(AUTH_SESSION_COOKIE_NAME)
        except AttributeError:
            return None
        return None if value in (None, "") else str(value)

    value: str | None = None
    for cookie in jar:
        if getattr(cookie, "name", None) != AUTH_SESSION_COOKIE_NAME:
            continue
        cookie_value = getattr(cookie, "value", None)
        if cookie_value not in (None, ""):
            value = str(cookie_value)
        else:
            value = None
    return value


def _request(method: str, path: str, json: dict[str, Any] | None = None) -> Any:
    if TestClient is None:
        raise ModuleNotFoundError("fastapi is required for the Streamlit API client.")

    with TestClient(create_app()) as client:
        for key, value in _cookie_state().items():
            client.cookies.set(key, value)

        response = client.request(method, f"/api{path}", json=json)
        updated_cookie = _jar_session_cookie_value(client.cookies)
        updated_cookies = _cookie_state()
        if updated_cookie in (None, ""):
            updated_cookies.pop(AUTH_SESSION_COOKIE_NAME, None)
        else:
            updated_cookies[AUTH_SESSION_COOKIE_NAME] = updated_cookie
        _sync_browser_cookie(updated_cookies.get(AUTH_SESSION_COOKIE_NAME))

    if response.status_code >= 400:
        payload = response.json() if response.content else {}
        if isinstance(payload, dict):
            detail = payload.get("detail", "API request failed.")
        else:
            detail = str(payload)
        raise ApiError(str(detail), response.status_code)

    if not response.content:
        return None
    return response.json()


def _path_with_query(path: str, **params: Any) -> str:
    query = urlencode(
        {key: value for key, value in params.items() if value is not None and value != ""},
        doseq=True,
    )
    return path if not query else f"{path}?{query}"


def _unwrap_collection(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ApiError(f"API returned an unexpected payload for {key}.", 500)


def get_auth_session() -> dict[str, Any]:
    return _request("GET", "/auth/session")


def login(username: str, password: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/login",
        json={"username": username, "password": password},
    )


def register(username: str, password: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/register",
        json={"username": username, "password": password},
    )


def logout() -> dict[str, Any]:
    return _request("POST", "/auth/logout")


def list_users() -> list[dict[str, Any]]:
    return _unwrap_collection(_request("GET", "/users"), "users")


def create_user(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/users", json=payload)


def verify_user(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/users/verify", json=payload)


def update_user(user_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/users/{user_id}", json=payload)


def delete_user(user_id: int) -> dict[str, Any]:
    return _request("DELETE", f"/users/{user_id}")


def get_settings() -> dict[str, Any]:
    return _request("GET", "/settings")


def save_settings(payload: SettingsPayload) -> dict[str, Any]:
    body = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return _request("POST", "/settings", json=body)


def list_llm_configs() -> list[dict[str, Any]]:
    return _request("GET", "/model-configs")


def create_llm_config(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/model-configs", json=payload)


def update_llm_config(config_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/model-configs/{config_id}", json=payload)


def delete_llm_config(config_id: int) -> bool:
    return _request("DELETE", f"/model-configs/{config_id}")


def test_llm_config(config_id: int) -> dict[str, Any]:
    return _request("POST", f"/model-configs/{config_id}/test")


def list_ai_models() -> list[dict[str, Any]]:
    return _request("GET", "/ai-models")


def create_ai_model(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/ai-models", json=payload)


def update_ai_model(model_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/ai-models/{model_id}", json=payload)


def delete_ai_model(model_id: int) -> bool:
    return _request("DELETE", f"/ai-models/{model_id}")


def show_ai_model(model_id: int) -> dict[str, Any]:
    return _request("GET", f"/ai-models/{model_id}")


def scan_ai_models(directory: str, *, recursive: bool = True) -> dict[str, Any]:
    return _request("POST", "/ai-models/scan", json={"directory": directory, "recursive": recursive})


def list_ai_model_preferences() -> list[dict[str, Any]]:
    return _request("GET", "/ai-model-preferences")


def create_ai_model_preference(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/ai-model-preferences", json=payload)


def update_ai_model_preference(preference_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/ai-model-preferences/{preference_id}", json=payload)


def delete_ai_model_preference(preference_id: int) -> bool:
    return _request("DELETE", f"/ai-model-preferences/{preference_id}")


def get_ai_model_executor_resources() -> dict[str, Any]:
    return _request("GET", "/ai-model-executor/resources")


def list_ai_hosts() -> list[dict[str, Any]]:
    return _request("GET", "/ai-hosts")


def create_ai_host(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/ai-hosts", json=payload)


def update_ai_host(host_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/ai-hosts/{host_id}", json=payload)


def delete_ai_host(host_id: int) -> dict[str, Any]:
    return _request("DELETE", f"/ai-hosts/{host_id}")


def show_ai_host(host_id: int) -> dict[str, Any]:
    return _request("GET", f"/ai-hosts/{host_id}")


def disable_ai_host(host_id: int) -> dict[str, Any]:
    return _request("POST", f"/ai-hosts/{host_id}/disable")


def inspect_ai_host_resources(bootstrap_password: str | None = None) -> list[dict[str, Any]]:
    params = {"bootstrap_password": bootstrap_password} if bootstrap_password else {}
    return _request("GET", "/ai-host-resources", params=params)


def validate_ai_host(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/ai-hosts/validate", json=payload)


def can_ai_model_run(model_id: int) -> dict[str, Any]:
    return _request("GET", f"/ai-model-executor/can-run/{model_id}")


def list_ai_model_executions(model_id: int | None = None) -> list[dict[str, Any]]:
    params = {"model_id": model_id} if model_id is not None else None
    return _request("GET", "/ai-model-executions", params=params)


def get_ai_model_execution_status(model_id: int | None = None) -> dict[str, Any]:
    params = {"model_id": model_id} if model_id is not None else None
    return _request("GET", "/ai-model-executions/status", params=params)


def start_ai_model_execution(model_id: int, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/ai-model-executor/start/{model_id}", json=payload)


def stop_ai_model_execution(model_id: int, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/ai-model-executor/stop/{model_id}", json=payload)


def list_modules() -> list[dict[str, Any]]:
    return _request("GET", "/modules")


def set_module_visibility(module_id: str, *, hidden: bool) -> dict[str, Any]:
    return _request("PATCH", f"/modules/{module_id}/visibility", json={"hidden": hidden})


def set_module_view_visibility(view_id: str, *, hidden: bool) -> dict[str, Any]:
    return _request("PATCH", f"/module-views/{view_id}/visibility", json={"hidden": hidden})


def set_module_view_order(module_id: str, view_id: str, *, new_index: int) -> dict[str, Any]:
    return _request("PATCH", f"/modules/{module_id}/views/{view_id}/order", json={"new_index": new_index})


def list_module_view_items(view_id: str) -> list[dict[str, Any]]:
    return _request("GET", f"/module-views/{view_id}/items")


def execute_module_command(command_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/module-commands/{command_id}", json={"payload": payload})


def start_loop_task(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/agent-loops/tasks", json=payload)


def list_loop_tasks(**params: Any) -> list[dict[str, Any]]:
    query = urlencode(
        {key: value for key, value in params.items() if value is not None and value != ""},
        doseq=True,
    )
    path = "/agent-loops/tasks" if not query else f"/agent-loops/tasks?{query}"
    payload = _request("GET", path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        tasks = payload.get("tasks")
        if isinstance(tasks, list):
            return tasks
    raise ApiError("API returned an unexpected payload for loop tasks.", 500)


def get_loop_task(task_id: str) -> dict[str, Any] | None:
    return _request("GET", f"/agent-loops/tasks/{task_id}")


def get_loop_task_transcript(task_id: str) -> dict[str, Any] | None:
    return _request("GET", f"/agent-loops/tasks/{task_id}/transcript")


def stop_loop_task(task_id: str) -> dict[str, Any] | None:
    return _request("POST", f"/agent-loops/tasks/{task_id}/stop")


def list_agents() -> list[dict[str, Any]]:
    return _request("GET", "/agents")


def create_agent(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/agents", json=payload)


def update_agent(agent_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/agents/{agent_id}", json=payload)


def delete_agent(agent_id: int) -> bool:
    return _request("DELETE", f"/agents/{agent_id}")


def list_groups() -> list[dict[str, Any]]:
    return _unwrap_collection(_request("GET", "/groups"), "groups")


def create_group(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/groups", json=payload)


def update_group(group_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/groups/{group_id}", json=payload)


def delete_group(group_id: int) -> bool:
    return _request("DELETE", f"/groups/{group_id}")


def list_group_members(group_id: int) -> list[dict[str, Any]]:
    return _unwrap_collection(_request("GET", f"/groups/{group_id}/members"), "members")


def add_group_member(group_id: int, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/groups/{group_id}/members", json=payload)


def set_group_membership_enabled(group_id: int, membership_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/groups/{group_id}/members/{membership_id}", json=payload)


def list_memories(**params: Any) -> list[dict[str, Any]]:
    query = urlencode(
        {key: value for key, value in params.items() if value is not None and value != ""},
        doseq=True,
    )
    path = "/memories" if not query else f"/memories?{query}"
    return _request("GET", path)


def search_memories(query: str, **params: Any) -> list[dict[str, Any]]:
    merged = {"query": query, **params}
    query_string = urlencode(
        {key: value for key, value in merged.items() if value is not None and value != ""},
        doseq=True,
    )
    return _request("GET", f"/memories/search?{query_string}")


def get_memory(memory_id: int) -> dict[str, Any] | None:
    return _request("GET", f"/memories/{memory_id}")


def create_memory(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/memories", json=payload)


def update_memory(memory_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/memories/{memory_id}", json=payload)


def archive_memory(memory_id: int) -> dict[str, Any]:
    return _request("POST", f"/memories/{memory_id}/archive")


def delete_memory(memory_id: int) -> dict[str, Any]:
    return _request("DELETE", f"/memories/{memory_id}")


def list_tool_definitions() -> list[dict[str, Any]]:
    return _request("GET", "/tools")


def create_tool_definition(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/tools", json=payload)


def get_tool_definition(tool_id: int) -> dict[str, Any] | None:
    return _request("GET", f"/tools/{tool_id}")


def update_tool_definition(tool_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/tools/{tool_id}", json=payload)


def assign_tool_to_agent(agent_id: int, tool_id: int, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/agents/{agent_id}/tools/{tool_id}", json=payload)


def unassign_tool_from_agent(agent_id: int, tool_id: int) -> bool:
    return _request("DELETE", f"/agents/{agent_id}/tools/{tool_id}")


def list_agent_tool_assignments(agent_id: int) -> list[dict[str, Any]]:
    return _request("GET", f"/agents/{agent_id}/tools/assignments")


def list_tools_available_to_agent(agent_id: int) -> list[dict[str, Any]]:
    return _request("GET", f"/agents/{agent_id}/tools/available")


def execute_tool_call(tool_id: int, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/tools/{tool_id}/execute", json=payload)


def create_agent_prompt(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/agent-prompts", json=payload)


def get_agent_prompt(prompt_id: int) -> dict[str, Any] | None:
    return _request("GET", f"/agent-prompts/{prompt_id}")


def update_agent_prompt(prompt_id: int, **payload: Any) -> dict[str, Any]:
    return _request("PUT", f"/agent-prompts/{prompt_id}", json=payload)


def get_compiled_agent_prompt(prompt_id: int, name: str | None = None) -> str:
    return _request("GET", _path_with_query(f"/agent-prompts/{prompt_id}/compiled", name=name))


def discussion_state() -> dict[str, Any]:
    return _request("GET", "/discussion/state")


def discussion_tree() -> dict[str, Any]:
    return _request("GET", "/discussions/tree")


def create_discussion(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/discussions", json=payload)


def update_discussion(discussion_id: str, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/discussions/{discussion_id}", json=payload)


def delete_discussion(discussion_id: str) -> dict[str, Any]:
    return _request("DELETE", f"/discussions/{discussion_id}")


def open_discussion(discussion_id: str) -> dict[str, Any]:
    return _request("POST", "/discussions/open", json={"discussion_id": discussion_id})


def prompt_discussion(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/discussion/prompt", json=payload)


def stop_discussion() -> dict[str, Any]:
    return _request("POST", "/discussion/stop")


def set_discussion_group_chat_mode(discussion_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/discussions/{discussion_id}/group-chat", json=payload)


def pause_group_chat() -> dict[str, Any]:
    return _request("POST", "/discussion/group-chat/pause")


def resume_group_chat() -> dict[str, Any]:
    return _request("POST", "/discussion/group-chat/resume")


def reset_discussion() -> dict[str, Any]:
    return _request("POST", "/discussion/reset")


def update_discussion_message(discussion_id: str, message_index: int, text: str) -> dict[str, Any]:
    return _request(
        "PATCH",
        f"/discussions/{discussion_id}/messages/{message_index}",
        json={"text": text},
    )


def delete_discussion_message(discussion_id: str, message_index: int) -> dict[str, Any]:
    return _request("DELETE", f"/discussions/{discussion_id}/messages/{message_index}")


def delete_discussion_messages(discussion_id: str, message_indices: list[int]) -> dict[str, Any]:
    return _request(
        "DELETE",
        f"/discussions/{discussion_id}/messages",
        json={"message_indices": message_indices},
    )


def list_wikis(**params: Any) -> list[dict[str, Any]]:
    query = urlencode(
        {key: value for key, value in params.items() if value is not None and value != ""},
        doseq=True,
    )
    path = "/wikis" if not query else f"/wikis?{query}"
    return _request("GET", path)


def create_wiki(**payload: Any) -> dict[str, Any]:
    return _request("POST", "/wikis", json=payload)


def get_wiki(wiki_id: str) -> dict[str, Any]:
    return _request("GET", f"/wikis/{wiki_id}")


def update_wiki(wiki_id: str, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/wikis/{wiki_id}", json=payload)


def delete_wiki(wiki_id: str) -> dict[str, Any]:
    return _request("DELETE", f"/wikis/{wiki_id}")


def get_wiki_tree(wiki_id: str) -> dict[str, Any]:
    return _request("GET", f"/wikis/{wiki_id}/tree")


def flatten_wiki_tree(wiki_id: str) -> list[dict[str, Any]]:
    return _request("GET", f"/wikis/{wiki_id}/flatten")


def search_wiki(wiki_id: str, query: str) -> list[dict[str, Any]]:
    query_string = urlencode({"query": query})
    return _request("GET", f"/wikis/{wiki_id}/search?{query_string}")


def create_wiki_branch(wiki_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/wikis/{wiki_id}/branches", json=payload)


def create_wiki_leaf(wiki_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/wikis/{wiki_id}/leaves", json=payload)


def update_wiki_node(node_id: str, **payload: Any) -> dict[str, Any]:
    return _request("PATCH", f"/wiki-nodes/{node_id}", json=payload)


def move_wiki_node(node_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/wiki-nodes/{node_id}/move", json=payload)


def reorder_wiki_node(node_id: str, **payload: Any) -> dict[str, Any]:
    return _request("POST", f"/wiki-nodes/{node_id}/reorder", json=payload)


def delete_wiki_node(node_id: str) -> dict[str, Any]:
    return _request("DELETE", f"/wiki-nodes/{node_id}")
