from types import SimpleNamespace
from unittest.mock import patch

from apmatia.api.http.routes import agent_routes


def test_create_new_agent_assigns_authenticated_owner():
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=42)

    with patch("apmatia.api.http.routes.agent_routes.require_session", return_value=session), patch(
        "apmatia.api.http.routes.agent_routes.create_agent",
        return_value={"id": 1, "name": "Planner"},
    ) as mock_create:
        result = agent_routes.create_new_agent(
            request,
            name="Planner",
            prompt_id=None,
            system_prompt_id=0,
            memory_id=0,
            rag_root_ids=[],
            tool_ids=[],
            default_model_id=None,
            active_model_id=None,
            workspace_root="",
            knowledge_root="",
            metadata={},
        )

    assert result == {"id": 1, "name": "Planner"}
    mock_create.assert_called_once_with(
        "Planner",
        owner_user_id=42,
        mode=0o600,
        prompt_id=None,
        system_prompt_id=0,
        memory_id=0,
        rag_root_ids=[],
        tool_ids=[],
        default_model_id=None,
        active_model_id=None,
        workspace_root="",
        knowledge_root="",
        metadata={},
    )


def test_update_agent_allows_patching_ownership_fields():
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=42)
    agent = SimpleNamespace(owner_user_id=1, owner_group_id=None)

    with patch("apmatia.api.http.routes.agent_routes.require_session", return_value=session), patch(
        "apmatia.api.http.routes.agent_routes.get_agent_manager"
    ) as mock_manager, patch(
        "apmatia.api.http.routes.agent_routes.can_write",
        return_value=True,
    ), patch(
        "apmatia.api.http.routes.agent_routes.update_agent",
        return_value={"id": 1, "name": "Planner"},
    ) as mock_update:
        mock_manager.return_value.get_agent.return_value = agent
        result = agent_routes.update_agent_by_id(
            request,
            1,
            owner_user_id=42,
            owner_group_id=7,
            name="Planner",
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

    assert result == {"id": 1, "name": "Planner"}
    mock_update.assert_called_once_with(
        1,
        owner_user_id=42,
        owner_group_id=7,
        name="Planner",
    )


def test_update_ownerless_agent_allows_repair_by_current_user():
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=42)
    agent = SimpleNamespace(owner_user_id=None, owner_group_id=None)

    with patch("apmatia.api.http.routes.agent_routes.require_session", return_value=session), patch(
        "apmatia.api.http.routes.agent_routes.get_agent_manager"
    ) as mock_manager, patch(
        "apmatia.api.http.routes.agent_routes.member_group_ids",
        return_value=set(),
    ), patch(
        "apmatia.api.http.routes.agent_routes.can_write",
        return_value=False,
    ), patch(
        "apmatia.api.http.routes.agent_routes.update_agent",
        return_value={"id": 1, "name": "Planner"},
    ) as mock_update:
        mock_manager.return_value.get_agent.return_value = agent
        result = agent_routes.update_agent_by_id(
            request,
            1,
            owner_user_id=42,
            owner_group_id=None,
            name="Planner",
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

    assert result == {"id": 1, "name": "Planner"}
    mock_update.assert_called_once_with(1, owner_user_id=42, name="Planner")


def test_update_locked_owned_agent_repairs_mode():
    request = SimpleNamespace()
    session = SimpleNamespace(user_id=42)
    agent = SimpleNamespace(owner_user_id=42, owner_group_id=None, mode=0)

    with patch("apmatia.api.http.routes.agent_routes.require_session", return_value=session), patch(
        "apmatia.api.http.routes.agent_routes.get_agent_manager"
    ) as mock_manager, patch(
        "apmatia.api.http.routes.agent_routes.member_group_ids",
        return_value=set(),
    ), patch(
        "apmatia.api.http.routes.agent_routes.can_write",
        return_value=False,
    ), patch(
        "apmatia.api.http.routes.agent_routes.update_agent",
        return_value={"id": 1, "name": "Planner"},
    ) as mock_update:
        mock_manager.return_value.get_agent.return_value = agent
        result = agent_routes.update_agent_by_id(
            request,
            1,
            owner_user_id=None,
            owner_group_id=None,
            name="Planner",
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

    assert result == {"id": 1, "name": "Planner"}
    mock_update.assert_called_once_with(1, mode=0o600, name="Planner")
