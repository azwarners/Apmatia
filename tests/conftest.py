"""Pytest configuration and shared fixtures for apmatia tests."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

existing_pythonpath = os.environ.get("PYTHONPATH")
if existing_pythonpath:
    if str(SRC_DIR) not in existing_pythonpath.split(":"):
        os.environ["PYTHONPATH"] = f"{SRC_DIR}:{existing_pythonpath}"
else:
    os.environ["PYTHONPATH"] = str(SRC_DIR)


# =============================================================================
# Streamlit Mocks
# =============================================================================

@pytest.fixture
def mock_streamlit(monkeypatch):
    """Pre-configured MagicMock for streamlit module."""
    mock_st = MagicMock()
    mock_st.sidebar = MagicMock()
    mock_st.title = MagicMock()
    mock_st.caption = MagicMock()
    mock_st.subheader = MagicMock()
    mock_st.write = MagicMock()
    mock_st.text_input = MagicMock(return_value="testuser")
    mock_st.text_area = MagicMock(return_value="Be concise")
    mock_st.color_picker = MagicMock(return_value="#ff6b6b")
    mock_st.file_uploader = MagicMock(return_value=[])
    mock_st.button = MagicMock(return_value=False)
    mock_st.form_submit_button = MagicMock(return_value=True)
    def _make_tabs(labels, **_kwargs):
        return [MagicMock() for _ in labels]

    mock_st.tabs = MagicMock(side_effect=_make_tabs)
    def _make_columns(spec, **_kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        columns = [MagicMock() for _ in range(count)]
        for column in columns:
            column.write = MagicMock()
            column.button = MagicMock(return_value=False)
        mock_st._columns_history.append(columns)
        mock_st._last_columns_result = columns
        return columns

    mock_st._columns_history = []
    mock_st._last_columns_result = []
    mock_st.columns = MagicMock(side_effect=_make_columns)
    mock_st.form = MagicMock()
    mock_st.header = MagicMock()
    mock_st.success = MagicMock()
    mock_st.error = MagicMock()
    mock_st.warning = MagicMock()
    mock_st.info = MagicMock()
    mock_st.divider = MagicMock()
    mock_st.container = MagicMock()
    mock_st.popover = MagicMock()
    mock_st.json = MagicMock()
    mock_st.selectbox = MagicMock(side_effect=lambda _label, options, index=0, **_kwargs: options[index])
    mock_st.multiselect = MagicMock(return_value=[])
    mock_st.checkbox = MagicMock(side_effect=lambda _label, value=False, **_kwargs: value)
    mock_st.number_input = MagicMock(side_effect=lambda _label, value=0, **_kwargs: value)
    mock_st.slider = MagicMock(side_effect=lambda _label, value=0, **_kwargs: value)
    mock_st.set_page_config = MagicMock()
    mock_st.set_option = MagicMock()
    mock_st.rerun = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.html = MagicMock()
    mock_st.query_params = {}
    mock_st.context = SimpleNamespace(cookies={})

    # Mock session state with dict-like behavior
    mock_session_state = {"auth_token": None, "authenticated_user": None}
    mock_st.session_state = mock_session_state

    mock_st.sidebar.title = MagicMock()
    mock_st.sidebar.caption = MagicMock()
    mock_st.sidebar.radio = MagicMock(return_value="Home")
    mock_st.sidebar.button = MagicMock(return_value=False)
    mock_st.sidebar.error = MagicMock()

    monkeypatch.setitem(__import__("sys").modules, "streamlit", mock_st)
    return mock_st


# =============================================================================
# User Management Mocks
# =============================================================================

@pytest.fixture
def mock_user():
    """Pre-configured MagicMock for a test user."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"
    return mock_user


@pytest.fixture
def mock_user_manager():
    """Pre-configured MagicMock for user manager."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"

    mock_manager = MagicMock()
    mock_manager.verify_user = MagicMock(return_value=True)
    mock_manager.create_user = MagicMock(return_value=mock_user)

    mock_repo = MagicMock()
    mock_repo.get_by_username = MagicMock(return_value=mock_user)
    mock_manager._user_repo = mock_repo

    return mock_manager


# =============================================================================
# Session Management Mocks
# =============================================================================

@pytest.fixture
def mock_session():
    """Pre-configured MagicMock for a test session."""
    mock_session = MagicMock()
    mock_session.token = "test_token_123"
    mock_session.user_id = 1
    mock_session.username = "testuser"
    return mock_session


@pytest.fixture
def mock_session_manager():
    """Pre-configured MagicMock for session manager."""
    mock_session = MagicMock()
    mock_session.token = "test_token_123"
    mock_session.user_id = 1
    mock_session.username = "testuser"

    mock_manager = MagicMock()
    mock_manager.create_session = MagicMock(return_value=mock_session)
    mock_manager.get_session = MagicMock(return_value=mock_session)

    return mock_manager


# =============================================================================
# Agent Management Mocks
# =============================================================================

@pytest.fixture
def mock_agent():
    """Pre-configured MagicMock for a test agent."""
    mock_agent = MagicMock()
    mock_agent.id = 1
    mock_agent.name = "Test Agent"
    mock_agent.description = ""
    mock_agent.status = MagicMock()
    mock_agent.status.value = "active"
    mock_agent.memory_backend = MagicMock()
    mock_agent.memory_backend.value = "vector"
    mock_agent.created_by_user_id = 1
    mock_agent.created_at = MagicMock()
    mock_agent.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    mock_agent.updated_at = MagicMock()
    mock_agent.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
    return mock_agent


@pytest.fixture
def mock_agent_manager():
    """Pre-configured MagicMock for agent manager."""
    mock_agent = MagicMock()
    mock_agent.id = 1
    mock_agent.name = "Test Agent"
    mock_agent.description = "Test Description"
    mock_agent.status = MagicMock()
    mock_agent.status.value = "active"
    mock_agent.memory_backend = MagicMock()
    mock_agent.memory_backend.value = "vector"
    mock_agent.created_by_user_id = 1
    mock_agent.created_at = MagicMock()
    mock_agent.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    mock_agent.updated_at = MagicMock()
    mock_agent.updated_at.isoformat.return_value = "2024-01-01T00:00:00"

    mock_manager = MagicMock()
    mock_manager.create_agent = MagicMock(return_value=mock_agent)
    return mock_manager


# =============================================================================
# Repository Mocks
# =============================================================================

@pytest.fixture
def mock_user_repository():
    """Pre-configured MagicMock for user repository."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "testuser"

    mock_repo = MagicMock()
    mock_repo.get_by_username = MagicMock(return_value=mock_user)
    return mock_repo
