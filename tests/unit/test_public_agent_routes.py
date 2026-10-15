from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from apmatia.api.http.routes import agent_routes, public_agent_routes
from apmatia.modules.agents.models import Agent


def test_public_listing_excludes_private_agents_and_limits_response_fields(monkeypatch):
    published = {
        "id": 7,
        "name": "Planner",
        "is_public": True,
        "memory_id": 0,
        "system_prompt_id": 0,
        "rag_root_ids": [],
        "tool_ids": [],
        "knowledge_root": "",
        "metadata": {},
        "default_model_id": 31,
        "active_model_id": None,
        "owner_user_id": 99,
        "workspace_root": "/private/path",
    }
    private = {**published, "id": 8, "is_public": False}
    manager = Mock()
    manager.get_agent_system_prompt.return_value = "compiled system prompt"
    model_manager = Mock()
    model_manager.get_config.return_value = SimpleNamespace(
        id=31,
        user_alias="Work model",
        backend="openai_compatible",
        provider_name="example-model",
        api_key="secret",
        model_url="http://internal/path",
    )
    monkeypatch.setattr(public_agent_routes, "list_agents", lambda: [published, private])
    monkeypatch.setattr(public_agent_routes, "get_agent_manager", lambda: manager)
    monkeypatch.setattr(public_agent_routes, "get_llm_config_manager", lambda: model_manager)

    result = public_agent_routes.list_public_agents()

    assert result == [
        {
            "id": 7,
            "name": "Planner",
            "system_prompt": "compiled system prompt",
            "model": {
                "id": 31,
                "alias": "Work model",
                "backend": "openai_compatible",
                "model": "example-model",
            },
        }
    ]
    assert "owner_user_id" not in result[0]
    assert "workspace_root" not in result[0]
    assert "api_key" not in result[0]["model"]
    assert "model_url" not in result[0]["model"]


def test_public_detail_hides_private_and_ineligible_agents(monkeypatch):
    manager = Mock()
    private_agent = SimpleNamespace(
        id=4,
        name="Private",
        is_public=False,
        memory_id=0,
        system_prompt_id=0,
        rag_root_ids=[],
        tool_ids=[],
        knowledge_root="",
        metadata={},
        default_model_id=None,
        active_model_id=None,
        owner_user_id=1,
        owner_group_id=None,
        prompt_id=None,
        workspace_root="/private/path",
    )
    manager.get_agent.return_value = private_agent
    monkeypatch.setattr(public_agent_routes, "get_agent_manager", lambda: manager)

    with pytest.raises(HTTPException) as error:
        public_agent_routes.get_public_agent(4)

    assert error.value.status_code == 404


def test_public_detail_returns_the_current_compiled_agent_contract(monkeypatch):
    agent = Agent(id=12, name="Luna", is_public=True)
    manager = Mock()
    manager.get_agent.return_value = agent
    manager.get_agent_system_prompt.return_value = "compiled Luna prompt"
    monkeypatch.setattr(public_agent_routes, "get_agent_manager", lambda: manager)
    model_manager = Mock()
    model_manager.get_config.return_value = None
    monkeypatch.setattr(public_agent_routes, "get_llm_config_manager", lambda: model_manager)

    result = public_agent_routes.get_public_agent(12)

    assert result == {
        "id": 12,
        "name": "Luna",
        "system_prompt": "compiled Luna prompt",
        "model": None,
    }
    manager.get_agent_system_prompt.assert_called_once_with(12)


def test_public_model_mapping_prefers_active_model_then_falls_back_to_default(monkeypatch):
    manager = Mock()
    manager.get_agent_system_prompt.return_value = "compiled prompt"
    model_manager = Mock()
    model_manager.get_config.side_effect = lambda model_id: SimpleNamespace(
        id=model_id,
        user_alias=f"alias-{model_id}",
        backend="openai_compatible",
        provider_name=f"provider-model-{model_id}",
    )
    monkeypatch.setattr(public_agent_routes, "get_agent_manager", lambda: manager)
    monkeypatch.setattr(public_agent_routes, "get_llm_config_manager", lambda: model_manager)

    active = public_agent_routes._public_agent(
        {"id": 1, "name": "Luna", "active_model_id": 22, "default_model_id": 11}
    )
    fallback = public_agent_routes._public_agent(
        {"id": 2, "name": "Luna", "active_model_id": None, "default_model_id": 11}
    )

    assert active["model"]["model"] == "provider-model-22"
    assert fallback["model"]["model"] == "provider-model-11"


def test_authenticated_agent_update_can_publish_and_unpublish(monkeypatch):
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=5)
    agent = Agent(
        id=1,
        owner_user_id=5,
        mode=0o600,
        name="Planner",
    )

    def persist_update(_agent_id, **updates):
        for key, value in updates.items():
            setattr(agent, key, value)
        return {"id": agent.id, "is_public": agent.is_public}

    update = Mock(side_effect=persist_update)
    manager = SimpleNamespace(get_agent=lambda _id: agent)
    monkeypatch.setattr(agent_routes, "require_session", lambda _request: session)
    monkeypatch.setattr(agent_routes, "member_group_ids", lambda _user_id: set())
    monkeypatch.setattr(agent_routes, "_can_update_agent", lambda *args, **kwargs: True)
    monkeypatch.setattr(agent_routes, "update_agent", update)
    monkeypatch.setattr(agent_routes, "get_agent_manager", lambda: manager)
    monkeypatch.setattr(public_agent_routes, "get_agent_manager", lambda: manager)

    empty_updates = dict(
        owner_user_id=None,
        owner_group_id=None,
        name=None,
        prompt_id=None,
        system_prompt_id=None,
        memory_id=None,
        rag_root_ids=None,
        tool_ids=None,
        default_model_id=None,
        active_model_id=None,
        workspace_root=None,
        knowledge_root=None,
        metadata=None,
    )
    result = agent_routes.update_agent_by_id(request, 1, **empty_updates, is_public=True)

    assert result == {"id": 1, "is_public": True}
    update.assert_called_once_with(1, is_public=True)
    agent.is_public = True
    update.reset_mock(return_value=True)
    update.return_value = {"id": 1, "is_public": False}

    result = agent_routes.update_agent_by_id(request, 1, **empty_updates, is_public=False)

    assert result == {"id": 1, "is_public": False}
    update.assert_called_once_with(1, is_public=False)
    with pytest.raises(HTTPException) as error:
        public_agent_routes.get_public_agent(1)
    assert error.value.status_code == 404


def test_anonymous_cannot_publish_or_unpublish_agents(monkeypatch):
    update = Mock()

    def reject_anonymous(_request):
        raise HTTPException(status_code=401, detail="Authentication required.")

    monkeypatch.setattr(agent_routes, "require_session", reject_anonymous)
    monkeypatch.setattr(agent_routes, "update_agent", update)

    with pytest.raises(HTTPException) as error:
        agent_routes.update_agent_by_id(SimpleNamespace(), 1, is_public=True)

    assert error.value.status_code == 401
    update.assert_not_called()


def test_non_owner_cannot_publish_another_users_agent(monkeypatch):
    request = SimpleNamespace()
    agent = Agent(id=1, owner_user_id=6, name="Private")
    update = Mock()
    monkeypatch.setattr(agent_routes, "require_session", lambda _request: SimpleNamespace(user_id=5))
    monkeypatch.setattr(agent_routes, "member_group_ids", lambda _user_id: set())
    monkeypatch.setattr(agent_routes, "can_write", lambda *_args: False)
    monkeypatch.setattr(agent_routes, "get_agent_manager", lambda: SimpleNamespace(get_agent=lambda _id: agent))
    monkeypatch.setattr(agent_routes, "update_agent", update)

    with pytest.raises(HTTPException) as error:
        agent_routes.update_agent_by_id(
            request,
            1,
            owner_user_id=None,
            owner_group_id=None,
            name=None,
            prompt_id=None,
            system_prompt_id=None,
            memory_id=None,
            rag_root_ids=None,
            tool_ids=None,
            default_model_id=None,
            active_model_id=None,
            is_public=True,
            workspace_root=None,
            knowledge_root=None,
            metadata=None,
        )

    assert error.value.status_code == 403
    update.assert_not_called()


def test_publication_rejects_private_capability_in_same_update(monkeypatch):
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=5)
    agent = SimpleNamespace(
        owner_user_id=5,
        owner_group_id=None,
        mode=0o600,
        is_public=False,
        memory_id=0,
        system_prompt_id=0,
        rag_root_ids=[],
        tool_ids=[],
        knowledge_root="",
        metadata={},
    )
    update = Mock()
    monkeypatch.setattr(agent_routes, "require_session", lambda _request: session)
    monkeypatch.setattr(agent_routes, "member_group_ids", lambda _user_id: set())
    monkeypatch.setattr(agent_routes, "_can_update_agent", lambda *args, **kwargs: True)
    monkeypatch.setattr(agent_routes, "update_agent", update)
    monkeypatch.setattr(agent_routes, "get_agent_manager", lambda: SimpleNamespace(get_agent=lambda _id: agent))

    with pytest.raises(HTTPException) as error:
        agent_routes.update_agent_by_id(
            request,
            1,
            owner_user_id=None,
            owner_group_id=None,
            name=None,
            prompt_id=None,
            system_prompt_id=None,
            memory_id=None,
            rag_root_ids=None,
            tool_ids=[23],
            default_model_id=None,
            active_model_id=None,
            workspace_root=None,
            knowledge_root=None,
            metadata=None,
            is_public=True,
        )

    assert error.value.status_code == 400
    update.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"memory_id": 1},
        {"system_prompt_id": 2},
        {"rag_root_ids": [3]},
        {"tool_ids": [4]},
        {"knowledge_root": "/private/knowledge"},
        {"metadata": {"internal": True}},
    ],
)
def test_agent_with_private_capabilities_cannot_be_published(changes):
    data = {
        "memory_id": 0,
        "system_prompt_id": 0,
        "rag_root_ids": [],
        "tool_ids": [],
        "knowledge_root": "",
        "metadata": {},
    }
    data.update(changes)
    agent = SimpleNamespace(**data)

    assert agent_routes._is_publication_eligible(agent) is False
