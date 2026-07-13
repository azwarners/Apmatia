from unittest.mock import patch

import pytest

from apmatia.core.settings_service import get_settings_payload, save_settings_payload


def _valid_payload() -> dict:
    return {
        "llama_server_log_dir": "/var/log/llama.cpp",
        "gguf_directories": "/models/gguf\n/alt/models/gguf",
        "auto_scan_gguf_directory": True,
        "llama_server_executable_path": "/usr/bin/llama-server",
        "llama_server_default_args": "--ctx-size 4096\n--host 0.0.0.0",
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
        ("ai_model_manager", "gguf_directories"): ["/models/gguf", "/alt/models/gguf"],
        ("ai_model_manager", "gguf_directory"): "/models/gguf",
        ("ai_model_manager", "auto_scan_gguf_directory"): True,
        ("ai_model_executor", "runtime_config", "executable_path"): "/usr/bin/llama-server",
        ("ai_model_executor", "runtime_config", "default_args"): ["--ctx-size 4096", "--host 0.0.0.0"],
        ("ui", "theme"): "light",
        ("ui", "font_family"): "monospace",
        ("ui", "accent_color"): "#123abc",
        ("ui", "font_size"): 17,
        ("ui", "title_bar_height"): 58,
        ("ui", "title_bar_font_size"): 21,
        ("ui", "terminal_background_color"): "#000000",
        ("ui", "terminal_text_color"): "#9dffad",
        ("ui", "terminal_border_color"): "rgba(110, 255, 170, 0.35)",
        ("ui", "terminal_muted_color"): "rgba(157, 255, 173, 0.72)",
    }

    def fake_get_config_value(*keys, default=None):
        return values.get(keys, default)

    with patch("apmatia.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload == {
        "llama_server_log_dir": "/var/log/llama.cpp",
        "gguf_directories": "/models/gguf\n/alt/models/gguf",
        "gguf_directory": "/models/gguf",
        "auto_scan_gguf_directory": True,
        "llama_server_executable_path": "/usr/bin/llama-server",
        "llama_server_default_args": "--ctx-size 4096\n--host 0.0.0.0",
        "theme": "light",
        "font_family": "monospace",
        "accent_color": "#123abc",
        "font_size": 17,
        "title_bar_height": 58,
        "title_bar_font_size": 21,
        "terminal_background_color": "#000000",
        "terminal_text_color": "#9dffad",
        "terminal_border_color": "rgba(110, 255, 170, 0.35)",
        "terminal_muted_color": "rgba(157, 255, 173, 0.72)",
    }


@patch("apmatia.core.settings_service.set_config_value")
def test_save_settings_payload_persists_ui_settings(mock_set_config_value):
    save_settings_payload(**_valid_payload())

    mock_set_config_value.assert_any_call("llama_server", "log_dir", value="/var/log/llama.cpp")
    mock_set_config_value.assert_any_call("ai_model_manager", "gguf_directories", value=["/models/gguf", "/alt/models/gguf"])
    mock_set_config_value.assert_any_call("ai_model_manager", "gguf_directory", value="/models/gguf")
    mock_set_config_value.assert_any_call("ai_model_manager", "auto_scan_gguf_directory", value=True)
    mock_set_config_value.assert_any_call("ai_model_executor", "runtime_config", "executable_path", value="/usr/bin/llama-server")
    mock_set_config_value.assert_any_call("ai_model_executor", "runtime_config", "default_args", value=["--ctx-size 4096", "--host 0.0.0.0"])
    mock_set_config_value.assert_any_call("ui", "theme", value="light")
    mock_set_config_value.assert_any_call("ui", "font_family", value="serif")
    mock_set_config_value.assert_any_call("ui", "accent_color", value="#123abc")
    mock_set_config_value.assert_any_call("ui", "font_size", value=18)
    mock_set_config_value.assert_any_call("ui", "title_bar_height", value=56)
    mock_set_config_value.assert_any_call("ui", "title_bar_font_size", value=20)
    mock_set_config_value.assert_any_call("ui", "terminal_background_color", value="#000000")
    mock_set_config_value.assert_any_call("ui", "terminal_text_color", value="#9dffad")
    mock_set_config_value.assert_any_call("ui", "terminal_border_color", value="rgba(110, 255, 170, 0.35)")
    mock_set_config_value.assert_any_call("ui", "terminal_muted_color", value="rgba(157, 255, 173, 0.72)")


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
        if keys == ("ai_model_manager", "gguf_directories"):
            return ["/models/gguf", "/alt/models/gguf"]
        if keys == ("ai_model_manager", "gguf_directory"):
            return None
        if keys == ("ai_model_manager", "auto_scan_gguf_directory"):
            return True
        if keys == ("ai_model_executor", "runtime_config", "executable_path"):
            return None
        if keys == ("ai_model_executor", "runtime_config", "default_args"):
            return []
        return default

    with patch.dict(
        "os.environ",
        {
            "APMATIA_LLAMA_SERVER_LOG_DIR": "/var/log/llama.cpp",
            "APMATIA_GGUF_DIRECTORY": "/models/gguf",
            "APMATIA_LLAMA_SERVER_EXECUTABLE_PATH": "/usr/bin/llama-server",
        },
        clear=True,
    ), patch("apmatia.core.settings_service.get_config_value", side_effect=fake_get_config_value):
        payload = get_settings_payload()

    assert payload["llama_server_log_dir"] == "/var/log/llama.cpp"
    assert payload["gguf_directories"] == "/models/gguf\n/alt/models/gguf"
    assert payload["gguf_directory"] == "/models/gguf"
    assert payload["llama_server_executable_path"] == "/usr/bin/llama-server"
    assert payload["llama_server_default_args"] == ""


@patch("apmatia.core.settings_service.set_config_value")
@patch("apmatia.modules.apmatia_ai_model_manager.AIModelManager")
def test_save_settings_payload_auto_scans_gguf_directory(mock_manager_cls, mock_set_config_value, tmp_path):
    gguf_dir = tmp_path / "models"
    gguf_dir.mkdir()
    (gguf_dir / "alpha-7b.gguf").write_bytes(b"gguf")

    save_settings_payload(
        llama_server_log_dir="",
        gguf_directories=str(gguf_dir),
        auto_scan_gguf_directory=True,
        llama_server_executable_path="llama-server",
        llama_server_default_args="",
        theme="light",
        font_family="serif",
        accent_color="#123abc",
        font_size=18,
        title_bar_height=56,
        title_bar_font_size=20,
    )

    mock_manager_cls.return_value.scan_gguf_directory.assert_called_once_with(gguf_dir, recursive=True)


@patch("apmatia.core.settings_service.set_config_value")
@patch("apmatia.modules.apmatia_ai_model_manager.AIModelManager")
def test_save_settings_payload_scans_gguf_directory_even_when_auto_scan_disabled(mock_manager_cls, mock_set_config_value, tmp_path):
    gguf_dir = tmp_path / "models"
    gguf_dir.mkdir()
    (gguf_dir / "alpha-7b.gguf").write_bytes(b"gguf")

    save_settings_payload(
        llama_server_log_dir="",
        gguf_directories=str(gguf_dir),
        auto_scan_gguf_directory=False,
        llama_server_executable_path="llama-server",
        llama_server_default_args="",
        theme="light",
        font_family="serif",
        accent_color="#123abc",
        font_size=18,
        title_bar_height=56,
        title_bar_font_size=20,
    )

    mock_manager_cls.return_value.scan_gguf_directory.assert_called_once_with(gguf_dir, recursive=True)


@patch("apmatia.core.settings_service.set_config_value")
def test_save_settings_payload_normalizes_multiple_gguf_directories(mock_set_config_value):
    save_settings_payload(
        llama_server_log_dir="",
        gguf_directories="/models/gguf, /alt/models/gguf\n\n /third/models ",
        auto_scan_gguf_directory=True,
        llama_server_executable_path="llama-server",
        llama_server_default_args="",
        theme="light",
        font_family="serif",
        accent_color="#123abc",
        font_size=18,
        title_bar_height=56,
        title_bar_font_size=20,
    )

    mock_set_config_value.assert_any_call("ai_model_manager", "gguf_directories", value=["/models/gguf", "/alt/models/gguf", "/third/models"])
    mock_set_config_value.assert_any_call("ai_model_manager", "gguf_directory", value="/models/gguf")
