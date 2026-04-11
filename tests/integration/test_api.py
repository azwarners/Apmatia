from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from src.api.http.app import app

client = TestClient(app)


@patch("src.api.http.routes.prompt_llm")
def test_api_prompt(mock_prompt_llm):
    mock_prompt_llm.return_value = "mocked api response"

    response = client.get("/api/prompt?prompt=Nick")

    assert response.status_code == 200
    assert response.json() == {"message": "mocked api response"}
    mock_prompt_llm.assert_called_once_with("Nick", output_dir=None)


@patch("src.api.http.routes.get_config_value")
def test_api_get_settings_includes_ui_preferences(mock_get_config_value):
    def fake_get_config(*keys, default=None):
        mapping = {
            ("llm", "backend"): "openai_compatible",
            ("llm", "openai_compatible", "base_url"): "http://localhost:5001",
            ("llm", "max_tokens"): 4096,
            ("discussion", "system_prompt"): "Be concise.",
            ("ui", "theme"): "light",
            ("ui", "font_family"): "serif",
            ("ui", "font_size"): 18,
            ("ui", "title_bar_height"): 60,
            ("ui", "title_bar_font_size"): 22,
        }
        return mapping.get(keys, default)

    mock_get_config_value.side_effect = fake_get_config

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {
        "backend": "openai_compatible",
        "model_url": "http://localhost:5001",
        "max_response_size": 4096,
        "system_prompt": "Be concise.",
        "theme": "light",
        "font_family": "serif",
        "font_size": 18,
        "title_bar_height": 60,
        "title_bar_font_size": 22,
    }


@patch("src.api.http.routes.discussion_state")
@patch("src.api.http.routes.set_config_value")
@patch("src.api.http.routes.get_config_value")
def test_api_save_settings_persists_theme_and_llm_fields(
    mock_get_config_value, mock_set_config_value, mock_discussion_state
):
    mock_get_config_value.return_value = "openai_compatible"
    payload = {
        "model_url": "http://example.local:5001",
        "max_response_size": 2048,
        "system_prompt": "Always help.",
        "theme": "light",
        "font_family": "monospace",
        "font_size": 20,
        "title_bar_height": 58,
        "title_bar_font_size": 21,
    }

    response = client.post("/api/settings", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "saved"}
    mock_set_config_value.assert_any_call(
        "llm", "openai_compatible", "base_url", value="http://example.local:5001"
    )
    mock_set_config_value.assert_any_call("llm", "max_tokens", value=2048)
    mock_set_config_value.assert_any_call("ui", "theme", value="light")
    mock_set_config_value.assert_any_call("ui", "font_family", value="monospace")
    mock_set_config_value.assert_any_call("ui", "font_size", value=20)
    mock_set_config_value.assert_any_call("ui", "title_bar_height", value=58)
    mock_set_config_value.assert_any_call("ui", "title_bar_font_size", value=21)
    mock_discussion_state.set_system_prompt.assert_called_once_with("Always help.")


def test_api_save_settings_rejects_invalid_font_size():
    payload = {
        "model_url": "http://example.local:5001",
        "max_response_size": 2048,
        "system_prompt": "",
        "theme": "dark",
        "font_family": "system-ui",
        "font_size": 99,
        "title_bar_height": 56,
        "title_bar_font_size": 20,
    }

    response = client.post("/api/settings", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Font size must be between 12 and 24."
