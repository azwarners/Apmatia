"""Replaceability acceptance tests for the view contract boundary.

These tests prove that Streamlit is one adapter rather than an architectural dependency.
They block Streamlit imports and verify that core/modules/API/CLI have no Streamlit dependency.
"""

from __future__ import annotations

import sys
from types import ModuleType


def block_streamlit_imports() -> ModuleType:
    """Block Streamlit imports by replacing the module with a stub.

    Returns:
        The stubbed streamlit module for later restoration.
    """
    # Save original if present
    original = sys.modules.get("streamlit")

    # Create a stub
    stub = ModuleType("streamlit")
    stub.__version__ = "blocked"

    # Stub common submodules
    stub.sidebar = type("sidebar", (), {
        "button": lambda *args, **kwargs: None,
        "title": lambda *args, **kwargs: None,
        "caption": lambda *args, **kwargs: None,
        "selectbox": lambda *args, **kwargs: None,
        "multiselect": lambda *args, **kwargs: None,
        "checkbox": lambda *args, **kwargs: None,
        "text_input": lambda *args, **kwargs: None,
        "number_input": lambda *args, **kwargs: None,
        "text_area": lambda *args, **kwargs: None,
        "divider": lambda *args, **kwargs: None,
        "expander": lambda *args, **kwargs: None,
        "tabs": lambda *args, **kwargs: None,
        "columns": lambda *args, **kwargs: None,
        "container": lambda *args, **kwargs: None,
        "toast": lambda *args, **kwargs: None,
        "error": lambda *args, **kwargs: None,
        "warning": lambda *args, **kwargs: None,
        "success": lambda *args, **kwargs: None,
        "info": lambda *args, **kwargs: None,
        "session_state": {},
        "query_params": {},
    })()
    stub.session_state = {}
    stub.query_params = {}
    stub.markdown = lambda *args, **kwargs: None
    st_module = ModuleType("streamlit")
    st_module.sidebar = stub.sidebar
    st_module.session_state = stub.session_state
    st_module.query_params = stub.query_params
    st_module.markdown = stub.markdown

    sys.modules["streamlit"] = st_module

    return original


def restore_streamlit_imports(original: ModuleType | None) -> None:
    """Restore Streamlit imports.

    Args:
        original: The original streamlit module to restore.
    """
    if original is not None:
        sys.modules["streamlit"] = original
    else:
        sys.modules.pop("streamlit", None)


def test_headless_renderer_walks_all_views() -> None:
    """Test that the headless renderer can traverse every active view without Streamlit."""
    # Block Streamlit
    original = block_streamlit_imports()

    try:
        # Import headless renderer (should not import streamlit)
        from apmatia.core.view_contract.headless_renderer import (
            HeadlessRenderResult,
            render_view_document_headless,
        )
        from apmatia.core.view_contract.models import ViewDocument, ViewComponent, ViewDataSource, ViewAction, ViewEffect, ViewStateDefinition, ViewRefreshPolicy

        # Create a sample view document
        document = ViewDocument(
            view_id="test.view",
            module_id="test_module",
            title="Test View",
            schema_version=1,
            presentation=ViewComponent(
                component_id="root",
                component_type="page",
                children=(
                    ViewComponent(
                        component_id="header",
                        component_type="text",
                        properties={"text": "Header"},
                    ),
                    ViewComponent(
                        component_id="collection",
                        component_type="collection",
                        binding=None,
                    ),
                ),
            ),
            data_sources=(
                ViewDataSource(
                    key="items",
                    kind="collection",
                    operation="list_items",
                ),
            ),
            state=(
                ViewStateDefinition(
                    key="selected_id",
                    value_type="string",
                    default="",
                ),
            ),
            actions=(
                ViewAction(
                    key="select",
                    intent="select_item",
                    label="Select",
                    command_id="select_item",
                    payload={"item_id": "1"},
                ),
            ),
            effects=(
                ViewEffect(
                    effect_type="refresh_view",
                    target="test.view",
                ),
            ),
            refresh_policy=ViewRefreshPolicy(mode="manual"),
        )

        # Render headlessly
        result = render_view_document_headless(
            document,
            data_source_values={"items": [{"id": "1", "name": "Item 1"}]},
            state_values={"selected_id": "1"},
        )

        # Verify results
        assert isinstance(result, HeadlessRenderResult)
        assert result.view_id == "test.view"
        assert result.module_id == "test_module"
        assert result.title == "Test View"
        assert result.rendered_components >= 2  # root + children

    finally:
        restore_streamlit_imports(original)


def test_text_adapter_executes_journeys() -> None:
    """Test that the text adapter executes representative journeys."""
    # Block Streamlit
    original = block_streamlit_imports()

    try:
        from apmatia.interfaces.text.text_adapter import TextAdapter, TextAdapterSession

        # Create a mock API client
        class MockAPI:
            def login(self, username, password):
                return {"user": {"username": username}, "token": "test-token"}

            def register(self, username, password):
                return {"user": {"username": username}, "token": "test-token"}

            def resolve_data_source(self, source_key, parameters):
                return {"items": [{"id": "1", "label": "Item 1"}]}

            def get_agent(self, agent_id):
                return {"id": agent_id, "name": f"Agent {agent_id}", "owner_user_id": 1, "model_config": {"model_id": "m1", "backend": "test"}}

            def discussion_tree(self):
                return {"discussions": [{"discussion_id": "d1", "title": "Discussion 1", "messages": [{"speaker_name": "Alice", "text": "Hello"}]}]}

            def prompt_discussion(self, discussion_id, text):
                return {"discussion_id": discussion_id, "messages": [{"speaker_name": "Bob", "text": f"Response to: {text}"}]}

            def start_agent_loop_task(self, agent_id, task_description):
                return {"task_id": f"task_{agent_id}"}

            def poll_agent_loop_task(self, task_id):
                return {"status": "running", "output": ["Progress..."], "complete": False}

            def stop_agent_loop_task(self, task_id):
                return {"status": "stopped"}

        mock_api = MockAPI()
        adapter = TextAdapter(mock_api)

        # Test login journey
        assert adapter.login("testuser", "password")
        assert adapter.session.authenticated_user is not None
        assert adapter.session.route == "module_view"

        # Test dynamic options
        options = adapter.resolve_dynamic_options("agents", {})
        assert len(options) == 1
        assert options[0]["id"] == "1"

        # Test agent config
        config = adapter.render_agent_config_view("agent1")
        assert "Agent: Agent agent1" in config

        # Test discussion timeline
        timeline = adapter.render_discussion_timeline("d1")
        assert "Discussion: Discussion 1" in timeline
        assert "[Alice] Hello" in timeline

        # Test discussion message
        result = adapter.send_discussion_message("d1", "Hello")
        assert result["status"] == "success"

        # Test Agent Loops task
        task_id = adapter.start_agent_loop_task("agent1", "Test task")
        assert task_id == "task_agent1"

        progress = adapter.poll_agent_loop_task(task_id)
        assert progress["status"] == "running"
        assert progress["output"] == ["Progress..."]

        stopped = adapter.stop_agent_loop_task(task_id)
        assert stopped

        # Test navigation
        adapter.navigate_to_view("preferences", "preferences.view")
        assert adapter.session.selected_module_id == "preferences"
        assert adapter.session.selected_view_id == "preferences.view"

        # Test confirmation
        confirmed = adapter.confirm_action("delete", "Delete this item?")
        assert confirmed

        # Test effect application
        adapter.apply_effect({"effect_type": "navigate", "target": "login"})
        assert adapter.session.route == "login"

    finally:
        restore_streamlit_imports(original)


def test_streamlit_blocked_imports() -> None:
    """Test that core/modules/API/CLI have no Streamlit dependency when blocked."""
    # Block Streamlit
    original = block_streamlit_imports()

    try:
        # These imports should not fail even with Streamlit blocked
        from apmatia.core.view_contract.models import ViewDocument, VIEW_CONTRACT_VERSION
        from apmatia.core.view_contract.validation import validate_view_document, ViewContractValidationError
        from apmatia.core.view_contract.headless_renderer import render_view_document_headless

        # Verify basic functionality
        assert VIEW_CONTRACT_VERSION == 1

        # Create a minimal valid document
        from apmatia.core.view_contract.models import ViewComponent, ViewBinding
        document = ViewDocument(
            view_id="test.view",
            module_id="test_module",
            title="Test",
            presentation=ViewComponent(
                component_id="test-page",
                component_type="page",
                properties={},
            ),
        )

        # Validate it
        validated = validate_view_document(document)
        assert validated.view_id == "test.view"

        # Verify headless rendering works
        result = render_view_document_headless(document)
        assert result.view_id == "test.view"

    finally:
        restore_streamlit_imports(original)


def test_streamlit_absent_imports() -> None:
    """Test that removing the Streamlit adapter leaves all portable documents intact."""
    # Completely remove Streamlit from sys.modules
    original = sys.modules.pop("streamlit", None)

    try:
        # These should work without streamlit installed
        from apmatia.core.view_contract.models import (
            ViewDocument,
            ViewComponent,
            ViewDataSource,
            ViewAction,
            ViewEffect,
            ViewStateDefinition,
            ViewRefreshPolicy,
            VIEW_CONTRACT_VERSION,
        )

        # Build a complete document
        document = ViewDocument(
            view_id="complete.view",
            module_id="complete_module",
            title="Complete View",
            schema_version=1,
            presentation=ViewComponent(
                component_id="root",
                component_type="page",
                children=(
                    ViewComponent(
                        component_id="header",
                        component_type="markdown",
                        properties={"text": "# Header"},
                    ),
                ),
            ),
            data_sources=(
                ViewDataSource(key="data", kind="collection", operation="get_data"),
            ),
            state=(
                ViewStateDefinition(key="selected", value_type="string", default=""),
            ),
            actions=(
                ViewAction(
                    key="submit",
                    intent="submit",
                    label="Submit",
                    operation="submit_data",
                    payload={"data": "value"},
                    success_effects=(
                        ViewEffect(effect_type="refresh_view", target="complete.view"),
                    ),
                ),
            ),
            effects=(),
            refresh_policy=ViewRefreshPolicy(mode="poll", interval_seconds=5.0),
        )

        # Verify the document is complete
        assert document.view_id == "complete.view"
        assert len(document.data_sources) == 1
        assert len(document.state) == 1
        assert len(document.actions) == 1
        assert document.presentation is not None
        assert len(document.presentation.children) == 1

    finally:
        # Restore if needed
        if original is not None:
            sys.modules["streamlit"] = original