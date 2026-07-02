from unittest.mock import patch

import pytest

from apmatia.core.settings_service import get_settings_payload, save_settings_payload


def _valid_payload() -> dict:
    return {
        "llama_server_log_dir": "/var/log/llama.cpp",
        "theme": "light",
        "font_family": "serif",
        "accent_color": "#123abc",
        "font_size": 18,
        "title_bar_height": 56,
        "title_bar_font_size": 20,
    }


def test_get_settings_payload_returns_ui_preferences():
    values = {
        ("llama_server", "log_dir"): "/var/log/llama.cpp",
        ("ui", "theme"): "light",
        ("ui", "font_family"): "monospace",
        ("ui", "accent_color"): "#123abc",
        ("ui", "font_size"): 17,
        ("ui", "title_bar_height"): 58,
        ("ui", "title_bar_font_size"): 21,
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload == {
        "llama_server_log_dir": "/var/log/llama.cpp",
        "theme": "light",
        "font_family": "monospace",
        "accent_color": "#123abc",
        "font_size": 17,
        "title_bar_height": 58,
        "title_bar_font_size": 21,
    }


@patch("apmatia.core.settings_service.set_config_value")
def test_save_settings_payload_persists_ui_settings(mock_set_config_value):
    save_settings_payload(**_valid_payload())

    mock_set_config_value.assert_any_call("llama_server", "log_dir", value="/var/log/llama.cpp")
    mock_set_config_value.assert_any_call("ui", "theme", value="light")
    mock_set_config_value.assert_any_call("ui", "font_family", value="serif")
    mock_set_config_value.assert_any_call("ui", "accent_color", value="#123abc")
    mock_set_config_value.assert_any_call("ui", "font_size", value=18)
    mock_set_config_value.assert_any_call("ui", "title_bar_height", value=56)
    mock_set_config_value.assert_any_call("ui", "title_bar_font_size", value=20)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("theme", "blue", "Theme must be 'system', 'dark', or 'light'."),
        ("accent_color", "red", "Accent color must be a valid hex color like #ff6b6b."),
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


def test_get_settings_payload_falls_back_to_llama_server_env():
    def fake_get_config_value(*keys, default=None):
        if keys == ("llama_server", "log_dir"):
            return None
        return default

    with patch.dict(
        "os.environ",
        {"APMATIA_LLAMA_SERVER_LOG_DIR": "/var/log/llama.cpp"},
        clear=True,
    ), patch("apmatia.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload["llama_server_log_dir"] == "/var/log/llama.cpp"
