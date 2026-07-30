"""Integration tests for model_id flow in the discussion module."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from apmatia.api.http.app import create_app


def test_discussion_prompt_with_model_id():
    """Test that discussion prompt endpoint correctly uses model_id from payload."""
    with patch(
        "apmatia.api.http.routes.discussion_routes.require_session",
        return_value={"user_id": 1, "username": "testuser"},
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_agent",
        return_value={"id": 1, "name": "Ada the Architect"},
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_llm_config"
    ) as mock_get_config, patch(
        "apmatia.api.http.routes.discussion_routes.prompt_llm"
    ) as mock_prompt:
        mock_get_config.return_value = {
            "id": 5,
            "name": "Qwen-80B",
            "model_url": "http://localhost:8080",
            "api_key": "sk-test123",
            "backend": "openai_compatible",
            "provider_name": "qwen-80b",
            "max_response_size": 8192,
        }
        mock_prompt.return_value = "Test response"

        response = TestClient(create_app()).post(
            "/api/discussion/prompt",
            json={"prompt": "Hello Ada", "agent_id": 1, "model_id": 5},
        )

        assert response.status_code == 200
    assert "Test response" in response.json()["result"]
    chat_messages = mock_prompt.call_args.kwargs["request_metadata"]["chat_messages"]
    assert chat_messages[-1] == {"role": "user", "content": "Hello Ada"}


def test_discussion_prompt_falls_back_to_agent_model():
    """Test that discussion prompt falls back to the agent's model."""
    with patch(
        "apmatia.api.http.routes.discussion_routes.require_session",
        return_value={"user_id": 1, "username": "testuser"},
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_agent"
    ) as mock_get_agent, patch(
        "apmatia.api.http.routes.discussion_routes.get_llm_config"
    ) as mock_get_config, patch(
        "apmatia.api.http.routes.discussion_routes.prompt_llm"
    ) as mock_prompt:
        mock_get_agent.return_value = {
            "id": 1,
            "name": "Ada the Architect",
            "active_model_id": 5,
            "default_model_id": 5,
        }
        mock_get_config.return_value = {
            "id": 5,
            "name": "Qwen-80B",
            "model_url": "http://localhost:8080",
            "api_key": "sk-test123",
            "backend": "openai_compatible",
        }
        mock_prompt.return_value = "Test response"

        response = TestClient(create_app()).post(
            "/api/discussion/prompt",
            json={"prompt": "Hello Ada", "agent_id": 1},
        )

        assert response.status_code == 200
        mock_get_config.assert_called_once_with(5)


def test_discussion_prompt_model_id_flow_in_docker():
    """Test that model_id flows correctly in the containerized test environment."""
    with patch(
        "apmatia.api.http.routes.discussion_routes.require_session",
        return_value={"user_id": 1, "username": "testuser"},
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_agent",
        return_value={"id": 1, "name": "Ada the Architect"},
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_llm_config"
    ) as mock_get_config, patch(
        "apmatia.api.http.routes.discussion_routes.prompt_llm"
    ) as mock_prompt:
        mock_get_config.return_value = {
            "id": 5,
            "name": "Qwen-80B",
            "model_url": "http://localhost:8080",
            "api_key": "sk-test123",
            "backend": "openai_compatible",
        }
        mock_prompt.return_value = "Test response"

        response = TestClient(create_app()).post(
            "/api/discussion/prompt",
            json={"prompt": "Hello Ada", "agent_id": 1, "model_id": 5},
        )

        assert response.status_code == 200
        llm_config = mock_prompt.call_args.kwargs["llm_config"]
        assert llm_config.model_url == "http://localhost:8080"


def test_group_prompt_resolves_each_member_model():
    """A group round uses each enabled agent's configured model independently."""
    members = [
        SimpleNamespace(member_kind="agent", agent_id=1, is_enabled=True),
        SimpleNamespace(member_kind="agent", agent_id=2, is_enabled=True),
    ]
    agents = {
        1: {"id": 1, "name": "Ada", "active_model_id": 5},
        2: {"id": 2, "name": "Beatrice", "active_model_id": 6},
    }
    configs = {
        5: {"id": 5, "model_url": "http://192.0.2.132:8080", "backend": "openai_compatible"},
        6: {"id": 6, "model_url": "http://192.0.2.133:8080", "backend": "openai_compatible"},
    }

    with patch(
        "apmatia.api.http.routes.discussion_routes.require_session",
        return_value=SimpleNamespace(user_id=1),
    ), patch(
        "apmatia.api.http.routes.discussion_routes.list_user_groups",
        return_value=[],
    ), patch(
        "apmatia.api.http.routes.discussion_routes.is_group_member",
        return_value=True,
    ), patch(
        "apmatia.api.http.routes.discussion_routes.list_group_members",
        return_value=members,
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_agent",
        side_effect=lambda agent_id: agents[agent_id],
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_llm_config",
        side_effect=lambda model_id: configs[model_id],
    ), patch(
        "apmatia.api.http.routes.discussion_routes.prompt_llm",
        side_effect=["Ada response", "Beatrice response"],
    ) as mock_prompt:
        response = TestClient(create_app()).post(
            "/api/discussion/group-prompt",
            json={"prompt": "Plan this", "group_id": 9},
        )

    assert response.status_code == 200
    assert [
        call.kwargs["llm_config"].model_url
        for call in mock_prompt.call_args_list
    ] == [
        "http://192.0.2.132:8080",
        "http://192.0.2.133:8080",
    ]
    assert [
        call.kwargs["request_metadata"]["speaker_name"]
        for call in mock_prompt.call_args_list
    ] == ["Ada", "Beatrice"]
    assert all(
        call.kwargs["request_metadata"]["chat_messages"][0]["role"] == "system"
        for call in mock_prompt.call_args_list
    )
    assert "You are Ada" in mock_prompt.call_args_list[0].kwargs["request_metadata"]["chat_messages"][0]["content"]
    assert "You are Beatrice" in mock_prompt.call_args_list[1].kwargs["request_metadata"]["chat_messages"][0]["content"]
    roster_prompt = mock_prompt.call_args_list[1].kwargs["request_metadata"]["chat_messages"][0]["content"]
    assert "Ada, Beatrice" in roster_prompt
    second_chat_messages = mock_prompt.call_args_list[1].kwargs["request_metadata"]["chat_messages"]
    assert {message["content"] for message in second_chat_messages} >= {
        "Ada: Ada response",
        "Respond as Beatrice to Nick's message. Respond only for yourself.",
    }


def test_discussion_snapshot_uses_agent_names_for_assistant_turns():
    """The transcript should show the agent name, not its internal numeric ID."""
    turns = [
        SimpleNamespace(turn_index=0, turn_kind="user", content="Hi", speaker_agent_id=None, metadata={}),
        SimpleNamespace(turn_index=1, turn_kind="assistant", content="Hello", speaker_agent_id=16, metadata={}),
    ]
    bundle = SimpleNamespace(turns=SimpleNamespace(list_by_discussion=lambda _discussion_id: turns))

    with patch(
        "apmatia.api.http.routes.discussion_routes.require_session",
        return_value=SimpleNamespace(user_id=1, username="Nick"),
    ), patch(
        "apmatia.modules.discuss.services.TopicManagementBundle",
        return_value=bundle,
    ), patch(
        "apmatia.api.http.routes.discussion_routes.get_agent",
        return_value={"id": 16, "name": "Ada the Architect"},
    ):
        response = TestClient(create_app()).get("/api/discussion/state?discussion_id=disc-test")

    assert response.status_code == 200
    assert response.json()["messages"][1]["speaker_name"] == "Ada the Architect"
