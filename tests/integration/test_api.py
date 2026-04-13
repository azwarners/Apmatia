from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from src.api.http.app import app

client = TestClient(app)


@patch("src.api.http.routes.prompt_routes.prompt_llm")
def test_api_prompt(mock_prompt_llm):
    mock_prompt_llm.return_value = "mocked api response"

    response = client.get("/api/prompt?prompt=Nick")

    assert response.status_code == 200
    assert response.json() == {"message": "mocked api response"}
    mock_prompt_llm.assert_called_once_with("Nick", output_dir=None)


@patch("src.api.http.routes.settings_routes.get_settings_payload")
def test_api_get_settings_includes_ui_preferences(mock_get_settings_payload):
    mock_get_settings_payload.return_value = {
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


@patch("src.api.http.routes.settings_routes.save_settings_payload")
def test_api_save_settings_persists_theme_and_llm_fields(mock_save_settings_payload):
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
    assert mock_save_settings_payload.call_count == 1


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
