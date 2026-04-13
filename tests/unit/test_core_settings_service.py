from unittest.mock import patch

import pytest

from src.core.settings_service import get_settings_payload, save_settings_payload


def _valid_payload() -> dict:
    return {
        "user_id": 7,
        "model_url": "http://example.local:5001",
        "max_response_size": 2048,
        "system_prompt": "Be concise",
        "theme": "light",
        "font_family": "serif",
        "font_size": 18,
        "title_bar_height": 56,
        "title_bar_font_size": 20,
    }


def test_get_settings_payload_prefers_openai_compatible_base_url():
    values = {
        ("llm", "backend"): "openai_compatible",
        ("llm", "openai_compatible", "base_url"): "http://openai.local:1234",
        ("llm", "max_tokens"): 4096,
        ("discussion", "system_prompt"): "Helpfully answer.",
        ("ui", "theme"): "light",
        ("ui", "font_family"): "monospace",
        ("ui", "font_size"): 17,
        ("ui", "title_bar_height"): 58,
        ("ui", "title_bar_font_size"): 21,
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("src.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload == {
        "backend": "openai_compatible",
        "model_url": "http://openai.local:1234",
        "max_response_size": 4096,
        "system_prompt": "Helpfully answer.",
        "theme": "light",
        "font_family": "monospace",
        "font_size": 17,
        "title_bar_height": 58,
        "title_bar_font_size": 21,
    }


def test_get_settings_payload_uses_kobold_url_when_backend_is_koboldcpp():
    values = {
        ("llm", "backend"): "koboldcpp",
        ("llm", "koboldcpp", "base_url"): "http://kobold.local:5001",
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("src.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload["backend"] == "koboldcpp"
    assert payload["model_url"] == "http://kobold.local:5001"


@patch("src.core.settings_service.set_config_value")
@patch("src.core.settings_service.get_config_value", return_value="openai_compatible")
@patch("src.core.settings_service.discussion_state")
def test_save_settings_payload_persists_openai_settings(
    mock_discussion_state,
    _mock_get_backend,
    mock_set_config_value,
):
    save_settings_payload(**_valid_payload())

    mock_set_config_value.assert_any_call(
        "llm",
        "openai_compatible",
        "base_url",
        value="http://example.local:5001",
    )
    mock_set_config_value.assert_any_call("llm", "max_tokens", value=2048)
    mock_set_config_value.assert_any_call("ui", "theme", value="light")
    mock_set_config_value.assert_any_call("ui", "font_family", value="serif")
    mock_set_config_value.assert_any_call("ui", "font_size", value=18)
    mock_set_config_value.assert_any_call("ui", "title_bar_height", value=56)
    mock_set_config_value.assert_any_call("ui", "title_bar_font_size", value=20)
    mock_discussion_state.set_system_prompt.assert_called_once_with(
        user_id=7,
        system_prompt="Be concise",
        member_group_ids=set(),
    )


@patch("src.core.settings_service.set_config_value")
@patch("src.core.settings_service.get_config_value", return_value="koboldcpp")
@patch("src.core.settings_service.discussion_state")
def test_save_settings_payload_persists_kobold_settings(
    _mock_discussion_state,
    _mock_get_backend,
    mock_set_config_value,
):
    save_settings_payload(**_valid_payload())

    mock_set_config_value.assert_any_call(
        "llm",
        "koboldcpp",
        "base_url",
        value="http://example.local:5001",
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("model_url", "   ", "Model URL cannot be empty."),
        ("max_response_size", 0, "Max response size must be at least 1."),
        ("theme", "blue", "Theme must be 'dark' or 'light'."),
        ("font_size", 11, "Font size must be between 12 and 24."),
        ("title_bar_height", 39, "Title bar height must be between 40 and 96."),
        ("title_bar_font_size", 41, "Title bar font size must be between 12 and 40."),
    ],
)
def test_save_settings_payload_validates_inputs(field, value, message):
    payload = _valid_payload()
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        save_settings_payload(**payload)
