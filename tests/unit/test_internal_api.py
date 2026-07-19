from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import patch

from apmatia.api.http.app import app, create_app
from apmatia.api.internal import discussions as internal_discussions
from apmatia.lib.model_management.models import LLM
from apmatia.api.internal.prompt_LLM import prompt_llm
from apmatia.api.internal import model_management


@patch("apmatia.api.internal.prompt_LLM.core_prompt_llm")
def test_internal_prompt(mock_core_prompt):
    mock_core_prompt.return_value = "mocked response"

    result = prompt_llm("Nick test", output_dir="/tmp/apmatia_logs")

    assert result == "mocked response"
    mock_core_prompt.assert_called_once_with(
        "Nick test",
        output_dir="/tmp/apmatia_logs",
        prompt_id=None,
        append_existing=False,
    )


def test_root_returns_fallback_page_when_legacy_web_ui_is_missing():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Apmatia is running" in response.text
    assert "http://127.0.0.1:8501" in response.text


def test_login_returns_fallback_page_when_legacy_web_ui_is_missing():
    client = TestClient(app)

    response = client.get("/login")

    assert response.status_code == 200
    assert "legacy browser UI is not included" in response.text


@patch("apmatia.api.http.routes.auth_routes.login_user")
def test_login_sets_a_30_day_cookie(mock_login_user):
    mock_login_user.return_value = SimpleNamespace(token="token123", username="nick")
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        json={"username": "nick", "password": "secret"},
    )

    assert response.status_code == 200
    assert "apmatia_session=token123" in response.headers.get("set-cookie", "")
    assert "max-age=2592000" in response.headers.get("set-cookie", "").lower()


@patch("apmatia.api.internal.model_management.get_llm_config_manager")
def test_model_management_serializes_slotted_llm_models(mock_get_manager):
    mock_manager = mock_get_manager.return_value
    mock_manager.list_configs.return_value = [
        LLM(id=1, user_alias="Local", provider_name="ollama", model_url="http://localhost:11434")
    ]
    mock_manager.create_config.return_value = LLM(
        id=2, user_alias="New", provider_name="ollama", model_url="http://localhost:11434"
    )
    mock_manager.update_config.return_value = LLM(
        id=3, user_alias="Updated", provider_name="ollama", model_url="http://localhost:11434"
    )

    assert model_management.list_llm_configs() == [
        {
            "id": 1,
            "user_alias": "Local",
            "metadata": {},
            "backend": "openai_compatible",
            "provider_name": "ollama",
            "model_url": "http://localhost:11434",
            "api_key": "",
            "max_response_size": 8192,
            "system_prompt": "",
        }
    ]
    assert model_management.create_llm_config(user_alias="New")["id"] == 2
    assert model_management.update_llm_config(3, user_alias="Updated")["id"] == 3


@patch("apmatia.api.http.routes.groups_routes.require_session")
@patch("apmatia.api.http.routes.groups_routes.is_group_owner", return_value=True)
@patch("apmatia.api.http.routes.groups_routes.list_group_members")
def test_group_members_route_lists_members(mock_list_group_members, mock_is_group_owner, mock_require_session):
    mock_require_session.return_value = SimpleNamespace(user_id=1, username="nick")
    mock_list_group_members.return_value = [
        {
            "id": 100,
            "group_id": 10,
            "user_id": 1,
            "role": "owner",
            "is_enabled": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    client = TestClient(app)

    response = client.get("/api/groups/10/members")

    assert response.status_code == 200
    assert response.json() == {
        "members": [
            {
                "id": 100,
                "group_id": 10,
                "user_id": 1,
                "role": "owner",
                "is_enabled": True,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    }
    mock_is_group_owner.assert_called_once()
    mock_list_group_members.assert_called()


@patch("apmatia.api.http.routes.groups_routes.require_session")
@patch("apmatia.api.http.routes.groups_routes.is_group_owner", return_value=True)
@patch("apmatia.api.http.routes.groups_routes.edit_group")
@patch("apmatia.api.http.routes.groups_routes.list_group_members", return_value=[{"id": 1, "user_id": 1, "role": "owner"}])
def test_group_edit_route_updates_group(
    mock_list_group_members, mock_edit_group, mock_is_group_owner, mock_require_session
):
    mock_require_session.return_value = SimpleNamespace(user_id=1, username="nick")
    mock_edit_group.return_value = SimpleNamespace(
        id=10,
        name="team-renamed",
        description="updated",
        created_by_user_id=1,
        created_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00+00:00"),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00+00:00"),
    )
    client = TestClient(app)

    response = client.patch("/api/groups/10", json={"name": "team-renamed", "description": "updated"})

    assert response.status_code == 200
    assert response.json()["group"]["name"] == "team-renamed"
    mock_edit_group.assert_called_once_with(
        group_id=10,
        name="team-renamed",
        description="updated",
        workspace_root=None,
    )
    mock_is_group_owner.assert_called_once()
    mock_list_group_members.assert_called_once_with(10)


@patch("apmatia.api.http.routes.groups_routes.require_session")
@patch("apmatia.api.http.routes.groups_routes.create_group")
def test_group_create_route_uses_authenticated_session(mock_create_group, mock_require_session):
    mock_require_session.return_value = SimpleNamespace(user_id=1, username="nick")
    mock_create_group.return_value = SimpleNamespace(
        id=11,
        name="team",
        description="core team",
        created_by_user_id=1,
        created_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00+00:00"),
        updated_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00+00:00"),
    )
    client = TestClient(app)

    response = client.post("/api/groups", json={"name": "team", "description": "core team"})

    assert response.status_code == 200
    assert response.json()["group"]["name"] == "team"
    mock_create_group.assert_called_once_with(
        name="team",
        created_by_user_id=1,
        description="core team",
        workspace_root="",
    )


@patch("apmatia.api.internal.discussions.discussion_state")
def test_internal_start_prompt_forwards_attachments(mock_discussion_state):
    attachments = [
        {"filename": "shot.png", "mime_type": "image/png", "data_base64": "Zm9v"}
    ]

    mock_discussion_state.start_prompt.return_value = "IDabc123"

    result = internal_discussions.start_prompt(
        user_id=1,
        prompt="hello",
        member_group_ids={7},
        agent_id=3,
        attachments=attachments,
    )

    assert result == "IDabc123"
    mock_discussion_state.start_prompt.assert_called_once_with(
        user_id=1,
        prompt="hello",
        member_group_ids={7},
        agent_id=3,
        attachments=attachments,
    )


@patch("apmatia.api.http.routes.discussion_routes.member_group_ids", return_value=set())
@patch("apmatia.api.http.routes.discussion_routes.require_session")
@patch("apmatia.api.http.routes.discussion_routes.discussions.snapshot")
def test_discussion_state_route_sanitizes_recursive_payload(mock_snapshot, mock_require_session, _mock_member_group_ids):
    recursive = {}
    recursive["self"] = recursive
    mock_snapshot.return_value = SimpleNamespace(
        discussion_id="IDabc123",
        is_streaming=False,
        last_error=None,
        agent_mode="discussion",
        chat_mode="round_robin",
        chat_pause_seconds=None,
        chat_is_paused=False,
        chat_turn_index=0,
        chat_coordinator_agent_id=None,
        system_prompt="",
        content="",
        messages=[],
        activity=recursive,
        llama_server_status=None,
    )
    mock_require_session.return_value = SimpleNamespace(user_id=1, username="nick")
    client = TestClient(app)

    response = client.get("/api/discussion/state")

    assert response.status_code == 200
    assert response.json()["activity"]["self"] == "<recursive>"
