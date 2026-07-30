from __future__ import annotations

from apmatia.core.registry import create_application_registry
from apmatia.core.view_contract import normalize_view_document


def _document() -> dict:
    registry = create_application_registry(include_development=True)
    view = next(view for view in registry.list_views() if view.view_id == "discuss.discussion.view")
    return normalize_view_document(view).to_dict()


def _components(component: dict) -> list[dict]:
    result = [component]
    for child in component.get("children", []):
        result.extend(_components(child))
    return result


def test_discussion_document_requires_an_agent_before_chatting():
    document = _document()
    state = {entry["key"]: entry for entry in document["state"]}
    assert state["selected_agent_id"]["default"] is None
    assert any(source["operation"] in {"list_agents", "agents:list"} for source in document["data_sources"])
    assert "send_message" in {action["key"] for action in document["actions"]}


def test_discussion_document_preserves_active_streaming_timeline_semantics():
    document = _document()
    component_types = {component["component_type"] for component in _components(document["presentation"])}
    actions = {action["key"]: action for action in document["actions"]}
    sources = {source["key"]: source for source in document["data_sources"]}
    component_ids = {component["component_id"] for component in _components(document["presentation"])}
    assert {"timeline", "message", "status", "panel"} <= component_types
    assert {"composer-panel", "message-input", "send-action"} <= component_ids
    assert sources["messages"]["refresh"]["cursor_key"] == "cursor"
    assert sources["messages"]["refresh"]["generation_key"] == "generation"
    assert actions["stop_message"]["command_id"] == "discuss.message.stop"
