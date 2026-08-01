"""Tests for the Linux client login support scaffolding."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from apmatia.interfaces.flet.common.api_client import ApmatiaApiClient
from apmatia.interfaces.flet.common.effects import EffectExecutor
from apmatia.interfaces.flet.common.errors import AuthenticationError
from apmatia.interfaces.flet.common.state import ClientState


@pytest.fixture
def mock_page():
    page = Mock()
    return page


@pytest.fixture
def api_client():
    return ApmatiaApiClient("http://test-api:8000")


def test_login_success(api_client):
    with patch.object(api_client.session, "request") as mock_request:
        mock_response = Mock()
        mock_response.json.return_value = {"status": "authenticated", "username": "testuser"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        result = api_client.login("testuser", "password")
    assert result["status"] == "authenticated"
    assert result["username"] == "testuser"


def test_login_failure(api_client):
    with patch.object(api_client.session, "request") as mock_request:
        import requests

        mock_error = requests.HTTPError("401 error")
        mock_response = Mock(status_code=401)
        mock_error.response = mock_response
        mock_request.side_effect = mock_error
        with pytest.raises(AuthenticationError):
            api_client.login("testuser", "wrong_password")


def test_client_state_authentication(mock_page):
    state = ClientState(mock_page)
    assert not state.is_authenticated
    state.set_authenticated({"user_id": 1, "username": "testuser"})
    assert state.is_authenticated
    assert state.username == "testuser"
    state.clear_authentication()
    assert not state.is_authenticated


def test_effect_executor_navigation_and_session_state(mock_page):
    state = ClientState(mock_page)
    executor = EffectExecutor(mock_page, state)
    executor.execute("navigate", {"route": "/home"})
    executor.execute("set_state", {"key": "test_key", "value": "test_value", "scope": "session"})
    assert mock_page.route == "/home"
    assert state.get_session("test_key") == "test_value"
