from __future__ import annotations

from dataclasses import replace

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import create_application_registry
from apmatia.core.view_contract import normalize_view_document
from apmatia.modules.agent_config.commands import COMMAND_DESCRIPTORS
from apmatia.modules.agent_config.module_views import ApmatiaAgentConfigModuleViewProvider
from apmatia.modules.agent_config.views import VIEW_DESCRIPTORS
from apmatia.modules.agent_alarms.views import VIEW_DESCRIPTORS as ALARM_VIEW_DESCRIPTORS, _ALARM_FORM_FIELDS
from apmatia.modules.ai_host_management.views import VIEW_DESCRIPTORS as HOST_VIEW_DESCRIPTORS
from apmatia.modules.agents.views import VIEW_DESCRIPTORS as AGENT_VIEW_DESCRIPTORS
from apmatia.modules.preferences.views import VIEW_DESCRIPTORS as PREFERENCE_VIEW_DESCRIPTORS
from apmatia.modules.users.views import VIEW_DESCRIPTORS as USER_VIEW_DESCRIPTORS
from apmatia.modules.agents.models import Agent


class _AgentManager:
    def __init__(self) -> None:
        self.agent = Agent(id=7, name="Planner", workspace_root="/old/workspace", knowledge_root="/old/knowledge")

    def list_agents(self):
        return [self.agent]

    def get_agent(self, agent_id: int):
        return self.agent if agent_id == 7 else None

    def update_agent(self, agent_id: int, **updates):
        assert agent_id == 7
        self.agent = replace(self.agent, **updates)
        return self.agent


def test_agent_config_provider_accepts_generic_item_identity(tmp_path):
    workspace = tmp_path / "workspace"
    knowledge = tmp_path / "knowledge"
    workspace.mkdir()
    knowledge.mkdir()
    manager = _AgentManager()
    provider = ApmatiaAgentConfigModuleViewProvider(manager)

    result = provider.execute_command(
        command=COMMAND_DESCRIPTORS[0],
        payload={
            "item_id": "7",
            "workspace_root": str(workspace),
            "knowledge_root": str(knowledge),
        },
        context=ModuleViewContext(user_id=1, group_ids=frozenset()),
    )

    assert result is not None
    assert result["status"] == "updated"
    assert result["item"]["id"] == 7
    assert result["item"]["workspace_root"] == str(workspace)
    assert result["warnings"] == []


def test_agent_config_contribution_is_contract_ready_without_renderer_token():
    view = VIEW_DESCRIPTORS[0]

    assert view.metadata["view_contract_ready"] is True
    assert view.metadata["presentation"].component_type == "page"


def test_agent_alarm_contribution_is_contract_ready_with_portable_option_sources():
    view = ALARM_VIEW_DESCRIPTORS[0]

    assert view.metadata["view_contract_ready"] is True
    # Check that data sources are declared for field options
    data_sources = {ds.key: ds for ds in view.metadata["data_sources"]}
    assert "agents" in data_sources
    assert "model_configs" in data_sources


def test_portable_alarm_sources_project_api_items_to_options(mock_streamlit):
    import importlib
    from unittest.mock import patch

    import apmatia.interfaces.streamlit.module_views.portable_page as portable_page
    from apmatia.core.view_contract import normalize_view_document

    portable_page = importlib.reload(portable_page)
    document = normalize_view_document(ALARM_VIEW_DESCRIPTORS[0]).to_dict()
    with patch.object(portable_page, "list_module_view_items", return_value=[]), patch.object(
        portable_page, "list_agents", return_value=[{"id": 7, "name": "Planner"}]
    ), patch.object(
        portable_page,
        "list_llm_configs",
        return_value=[{"id": 11, "user_alias": "Fast alias", "name": "Fallback"}],
    ):
        sources = portable_page._load_data_sources(document)

    assert sources["agents"] == [{"label": "Planner", "value": 7}]
    assert sources["model_configs"] == [{"label": "Fast alias", "value": 11}]


def test_contract_field_renderer_resolves_declared_option_source(mock_streamlit):
    import importlib

    import apmatia.interfaces.streamlit.module_views.contract_renderer as contract_renderer

    contract_renderer = importlib.reload(contract_renderer)
    mock_streamlit.selectbox.return_value = "Planner"

    value = contract_renderer._render_field(
        {
            "key": "agent_id",
            "label": "Agent",
            "field_type": "select",
            "options_source": {"source": "agents"},
        },
        data_sources={"agents": [{"label": "Planner", "value": 7}]},
    )

    assert value == 7
    mock_streamlit.selectbox.assert_called_once_with("Agent", ["Planner"], index=0, help=None)


def test_ai_host_documents_are_contract_ready_with_executable_form_actions():
    from apmatia.core.view_contract import normalize_view_document

    host_view = next(view for view in HOST_VIEW_DESCRIPTORS if view.view_id.endswith("hosts.view"))
    resource_view = next(view for view in HOST_VIEW_DESCRIPTORS if view.view_id.endswith("resources.view"))
    document = normalize_view_document(host_view).to_dict()
    actions = {action["key"]: action for action in document["actions"]}

    assert host_view.metadata["view_contract_ready"] is True
    assert resource_view.metadata["view_contract_ready"] is True
    assert actions["prepare_ssh_key"]["scope"] == "form"
    assert actions["prepare_ssh_key"]["command_id"] == "ai_host_management.hosts.prepare_ssh_key"
    assert actions["prepare_ssh_copy_command"]["scope"] == "form"
    assert actions["disable"]["confirmation"] is True


def test_agents_management_is_a_portable_crud_document():
    from apmatia.core.view_contract import normalize_view_document

    view = AGENT_VIEW_DESCRIPTORS[0]
    document = normalize_view_document(view).to_dict()
    actions = {action["key"]: action for action in document["actions"]}

    assert view.metadata["view_contract_ready"] is True
    assert view.metadata["presentation"].component_type == "page"
    assert {"create", "edit", "clone", "delete"} <= actions.keys()
    assert actions["clone"]["command_id"] == "agents.clone"
    assert any(source.operation == "model_configs:list" for source in view.metadata["data_sources"])


def test_users_groups_and_memberships_are_a_portable_crud_document():
    from apmatia.core.view_contract import normalize_view_document

    view = USER_VIEW_DESCRIPTORS[0]
    document = normalize_view_document(view).to_dict()
    fields = {
        child["properties"]["key"]
        for component in document["presentation"]["children"]
        if component["component_type"] == "form"
        for child in component["children"]
    }

    assert view.metadata["view_contract_ready"] is True
    assert view.metadata["presentation"].component_type == "page"
    assert {"item_kind", "group_id", "member_kind", "agent_id", "role"} <= fields


def test_module_management_is_a_portable_catalog_document():
    from apmatia.core.view_contract import normalize_view_document

    view = PREFERENCE_VIEW_DESCRIPTORS[1]
    document = normalize_view_document(view).to_dict()
    actions = {action["key"]: action for action in document["actions"]}

    assert view.metadata["view_contract_ready"] is True
    assert view.metadata["presentation"].component_type == "page"
    assert actions["edit"]["command_id"] == "preferences.update_catalog_item"


def test_discuss_and_agent_loops_registered_documents_preserve_portable_behavior():
    registry = create_application_registry(include_development=True)
    documents = {
        view.view_id: normalize_view_document(view).to_dict()
        for view in registry.list_views()
        if view.view_id in {"discuss.discussion.view", "agent_loops.loops.view"}
    }

    discussion = documents["discuss.discussion.view"]
    discussion_actions = {action["key"] for action in discussion["actions"]}
    discussion_sources = {source["key"] for source in discussion["data_sources"]}
    assert {"send_message", "stop_message", "edit_message", "delete_message", "open_discussion"} <= discussion_actions
    assert {"messages", "activity", "discussions"} <= discussion_sources
    assert discussion["refresh_policy"]["cursor_key"] == "cursor"
    assert discussion["refresh_policy"]["generation_key"] == "generation"

    loops = documents["agent_loops.loops.view"]
    loop_actions = {action["key"] for action in loops["actions"]}
    loop_sources = {source["key"] for source in loops["data_sources"]}
    component_types: set[str] = set()

    def visit(component):
        component_types.add(component["component_type"])
        for child in component.get("children", []):
            visit(child)

    visit(loops["presentation"])
    assert {"launch_task", "stop_task", "select_contact"} <= loop_actions
    assert {"contacts", "tasks", "current_task", "workspace", "knowledge"} <= loop_sources
    assert {"terminal", "checklist", "progress", "tree"} <= component_types
    assert loops["refresh_policy"]["cursor_key"] == "cursor"
    assert loops["refresh_policy"]["generation_key"] == "generation"
