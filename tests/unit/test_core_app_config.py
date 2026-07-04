from unittest.mock import MagicMock, patch

import os
import tempfile
from pathlib import Path

import pytest

from apmatia.core import app_config


class TestResolveConfigDir:
    def test_uses_env_override_when_set(self):
        with patch.dict(os.environ, {"APMATIA_CONFIG_DIR": "/custom/config/path"}):
            result = app_config._resolve_config_dir()
        assert result == Path("/custom/config/path")

    def test_expands_user_in_env_override(self):
        with patch.dict(os.environ, {"APMATIA_CONFIG_DIR": "~/my_config"}):
            result = app_config._resolve_config_dir()
        assert result == Path.home() / "my_config"

    def test_uses_preferred_config_dir_when_no_env_override(self):
        with patch.dict(os.environ, {}, clear=True):
            result = app_config._resolve_config_dir()
        assert result == app_config.PREFERRED_CONFIG_DIR

    def test_falls_back_to_temp_dir_on_oserror(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("apmatia.core.app_config.PREFERRED_CONFIG_DIR") as mock_preferred:
                mock_preferred.mkdir.side_effect = OSError("Permission denied")
                result = app_config._resolve_config_dir()
        expected_fallback = Path(tempfile.gettempdir()) / "apmatia"
        assert result == expected_fallback

    def test_falls_back_to_temp_dir_when_preferred_dir_is_not_writable(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("apmatia.core.app_config.PREFERRED_CONFIG_DIR") as mock_preferred:
                mock_preferred.mkdir.return_value = None
                with patch("apmatia.core.app_config._dir_is_writable", return_value=False):
                    result = app_config._resolve_config_dir()
        expected_fallback = Path(tempfile.gettempdir()) / "apmatia"
        assert result == expected_fallback


class TestDefaultConfig:
    def test_returns_expected_structure(self):
        config = app_config._default_config()

        assert "llm" in config
        assert "discussion" in config
        assert "ai_model_manager" in config
        assert "ai_model_executor" in config
        assert "llama_server" in config
        assert "ui" in config

    def test_llm_config_structure(self):
        config = app_config._default_config()

        assert config["llm"]["model_name"] == "default"
        assert config["llm"]["max_tokens"] == 8192
        assert config["llm"]["backend"] == "openai_compatible"
        assert "openai_compatible" in config["llm"]
        assert "koboldcpp" in config["llm"]

    def test_discussion_config_structure(self):
        config = app_config._default_config()

        assert config["discussion"]["current_discussion_id"] is None
        assert config["discussion"]["system_prompt"] == ""

    def test_ui_config_structure(self):
        config = app_config._default_config()

        assert config["ui"]["theme"] == "dark"
        assert config["ui"]["font_family"] == "system-ui"
        assert config["ui"]["accent_color"] == "#ff6b6b"
        assert config["ui"]["font_size"] == 16

    def test_llama_server_config_structure(self):
        config = app_config._default_config()

        assert config["llama_server"]["log_dir"] == ""

    def test_ai_model_manager_config_structure(self):
        config = app_config._default_config()

        assert config["ai_model_manager"]["gguf_directory"] == ""
        assert config["ai_model_manager"]["auto_scan_gguf_directory"] is True

    def test_ai_model_executor_config_structure(self):
        config = app_config._default_config()

        runtime_config = config["ai_model_executor"]["runtime_config"]
        assert runtime_config["executable_path"] == "llama-server"
        assert runtime_config["default_args"] == []
        assert runtime_config["stop_conflicting_models"] is True


class TestMergeDicts:
    def test_merges_simple_dicts(self):
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}
        result = app_config._merge_dicts(base, overlay)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merges_nested_dicts(self):
        base = {"a": {"x": 1, "y": 2}}
        overlay = {"a": {"y": 3, "z": 4}}
        result = app_config._merge_dicts(base, overlay)

        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_preserves_base_values_not_in_overlay(self):
        base = {"a": 1, "b": 2}
        overlay = {"c": 3}
        result = app_config._merge_dicts(base, overlay)

        assert result == {"a": 1, "b": 2, "c": 3}

    def test_overwrites_base_values_with_overlay(self):
        base = {"a": 1, "b": 2}
        overlay = {"a": 10, "b": 20}
        result = app_config._merge_dicts(base, overlay)

        assert result == {"a": 10, "b": 20}

    def test_does_not_modify_original_dicts(self):
        base = {"a": 1}
        overlay = {"a": 2}
        app_config._merge_dicts(base, overlay)

        assert base == {"a": 1}
        assert overlay == {"a": 2}


class TestSetNested:
    def test_sets_top_level_key(self):
        config = {}
        app_config._set_nested(config, ("key",), "value")
        assert config == {"key": "value"}

    def test_sets_nested_key(self):
        config = {}
        app_config._set_nested(config, ("a", "b", "c"), "value")
        assert config == {"a": {"b": {"c": "value"}}}

    def test_creates_intermediate_dicts(self):
        config = {"a": None}
        app_config._set_nested(config, ("a", "b", "c"), "value")
        assert config == {"a": {"b": {"c": "value"}}}

    def test_overwrites_existing_value(self):
        config = {"a": {"b": {"c": "old"}}}
        app_config._set_nested(config, ("a", "b", "c"), "new")
        assert config == {"a": {"b": {"c": "new"}}}


class TestSeedFromEnv:
    def test_seeds_llm_model_name(self):
        config = app_config._default_config()
        with patch.dict(os.environ, {"LLM_MODEL": "test-model"}):
            result = app_config._seed_from_env(config)
        assert result["llm"]["model_name"] == "test-model"

    def test_seeds_llm_max_tokens(self):
        config = app_config._default_config()
        with patch.dict(os.environ, {"LLM_MAX_TOKENS": "4096"}):
            result = app_config._seed_from_env(config)
        assert result["llm"]["max_tokens"] == 4096

    def test_skips_empty_env_values(self):
        config = app_config._default_config()
        with patch.dict(os.environ, {"LLM_MODEL": ""}):
            result = app_config._seed_from_env(config)
        assert result["llm"]["model_name"] == "default"

    def test_handles_invalid_max_tokens(self):
        config = app_config._default_config()
        with patch.dict(os.environ, {"LLM_MAX_TOKENS": "not-a-number"}):
            result = app_config._seed_from_env(config)
        assert result["llm"]["max_tokens"] == 8192

    def test_seeds_all_llm_configurations(self):
        config = {"llm": {}}
        env_vars = {
            "LLM_MODEL": "gpt-4",
            "LLM_MAX_TOKENS": "16384",
            "YSPARR_TEXT2TEXT_BACKEND": "koboldcpp",
            "OPENAI_COMPAT_BASE_URL": "http://localhost:8000",
            "OPENAI_COMPAT_API_KEY": "test-key",
            "OPENAI_COMPAT_MODEL": "gpt-3.5-turbo",
            "KOBOLDCPP_URL": "http://localhost:8001",
            "APMATIA_GGUF_DIRECTORY": "/models/gguf",
            "APMATIA_LLAMA_SERVER_EXECUTABLE_PATH": "/usr/bin/llama-server",
            "APMATIA_LLAMA_SERVER_DEFAULT_ARGS": "--ctx-size 4096 --host 0.0.0.0",
            "APMATIA_LLAMA_SERVER_LOG_DIR": "/var/log/llama.cpp",
        }
        with patch.dict(os.environ, env_vars):
            result = app_config._seed_from_env(config)

        assert result["llm"]["model_name"] == "gpt-4"
        assert result["llm"]["max_tokens"] == 16384
        assert result["llm"]["backend"] == "koboldcpp"
        assert result["llm"]["openai_compatible"]["base_url"] == "http://localhost:8000"
        assert result["llm"]["openai_compatible"]["api_key"] == "test-key"
        assert result["llm"]["openai_compatible"]["model_name"] == "gpt-3.5-turbo"
        assert result["llm"]["koboldcpp"]["base_url"] == "http://localhost:8001"
        assert result["ai_model_manager"]["gguf_directory"] == "/models/gguf"
        assert result["ai_model_executor"]["runtime_config"]["executable_path"] == "/usr/bin/llama-server"
        assert result["ai_model_executor"]["runtime_config"]["default_args"] == ["--ctx-size", "4096", "--host", "0.0.0.0"]
        assert result["llama_server"]["log_dir"] == "/var/log/llama.cpp"

    def test_does_not_override_existing_saved_values_with_env_defaults(self):
        config = {
            "ai_model_manager": {
                "gguf_directory": "/saved/models",
                "gguf_directories": ["/saved/models", "/saved/vision"],
            }
        }
        env_vars = {
            "APMATIA_GGUF_DIRECTORY": "/startup/models",
            "APMATIA_GGUF_DIRECTORIES": "/startup/models:/startup/vision",
        }
        with patch.dict(os.environ, env_vars):
            result = app_config._seed_from_env(config)

        assert result["ai_model_manager"]["gguf_directory"] == "/saved/models"
        assert result["ai_model_manager"]["gguf_directories"] == ["/saved/models", "/saved/vision"]


class TestMigrateLegacyState:
    def test_returns_config_unchanged_when_no_legacy_file(self):
        config = {"discussion": {}}
        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = False
            result = app_config._migrate_legacy_state(config)
        assert result == config

    def test_migrates_current_discussion_id(self):
        config = {"discussion": {}}
        legacy_data = {"current_discussion_id": 123}

        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = True
            with patch(
                "apmatia.core.app_config.load_config_file", return_value=legacy_data
            ):
                result = app_config._migrate_legacy_state(config)

        assert result["discussion"]["current_discussion_id"] == "123"

    def test_migrates_system_prompt(self):
        config = {"discussion": {}}
        legacy_data = {"system_prompt": "Test prompt"}

        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = True
            with patch(
                "apmatia.core.app_config.load_config_file", return_value=legacy_data
            ):
                result = app_config._migrate_legacy_state(config)

        assert result["discussion"]["system_prompt"] == "Test prompt"

    def test_preserves_existing_discussion_values(self):
        config = {"discussion": {"current_discussion_id": "456"}}
        legacy_data = {"current_discussion_id": 123}

        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = True
            with patch(
                "apmatia.core.app_config.load_config_file", return_value=legacy_data
            ):
                result = app_config._migrate_legacy_state(config)

        assert result["discussion"]["current_discussion_id"] == "456"

    def test_handles_load_config_file_exception(self):
        config = {"discussion": {}}

        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = True
            with patch(
                "apmatia.core.app_config.load_config_file", side_effect=Exception("Error")
            ):
                result = app_config._migrate_legacy_state(config)

        assert result == config

    def test_handles_non_dict_legacy_data(self):
        config = {"discussion": {}}

        with patch("apmatia.core.app_config.LEGACY_STATE_FILE") as mock_legacy_path:
            mock_legacy_path.exists.return_value = True
            with patch("apmatia.core.app_config.load_config_file", return_value="not a dict"):
                result = app_config._migrate_legacy_state(config)

        assert result == config


class TestLoadAppConfig:
    def test_merges_default_config_with_loaded_config(self):
        loaded_config = {"llm": {"model_name": "custom"}}

        with patch(
            "apmatia.core.app_config.load_config_file", return_value=loaded_config
        ):
            with patch(
                "apmatia.core.app_config._migrate_legacy_state", side_effect=lambda x: x
            ):
                with patch(
                    "apmatia.core.app_config._seed_from_env", side_effect=lambda x: x
                ):
                    with patch("apmatia.core.app_config._config_file", return_value=Path("/tmp/test_config.json")):
                        result = app_config.load_app_config()

        assert result["llm"]["model_name"] == "custom"
        assert result["llm"]["max_tokens"] == 8192

    def test_handles_non_dict_loaded_config(self):
        with patch("apmatia.core.app_config.load_config_file", return_value="not a dict"):
            with patch(
                "apmatia.core.app_config._migrate_legacy_state", side_effect=lambda x: x
            ):
                with patch(
                    "apmatia.core.app_config._seed_from_env", side_effect=lambda x: x
                ):
                    with patch("apmatia.core.app_config._config_file", return_value=Path("/tmp/test_config.json")):
                        result = app_config.load_app_config()

        assert result["llm"]["model_name"] == "default"

    def test_saves_config_when_seeded_differently(self):
        loaded_config = {"llm": {"model_name": "custom"}}

        with patch(
            "apmatia.core.app_config.load_config_file", return_value=loaded_config
        ):
            with patch(
                "apmatia.core.app_config._migrate_legacy_state", side_effect=lambda x: x
            ):
                with patch(
                    "apmatia.core.app_config._seed_from_env",
                    side_effect=lambda x: {**x, "llm": {**x["llm"], "model_name": "seeded"}},
                ):
                    with patch("apmatia.core.app_config.save_app_config") as mock_save:
                        with patch("apmatia.core.app_config._config_file", return_value=Path("/tmp/test_config.json")):
                            result = app_config.load_app_config()

        assert result["llm"]["model_name"] == "seeded"
        mock_save.assert_called_once()


class TestSaveAppConfig:
    def test_saves_config_to_file(self):
        config = {"test": "value"}
        with patch("apmatia.core.app_config.save_config_file") as mock_save:
            with patch("apmatia.core.app_config._config_file", return_value=Path("/tmp/test_config.json")) as mock_config_file:
                app_config.save_app_config(config)
        mock_save.assert_called_once_with(mock_config_file.return_value, config)


class TestGetConfigValue:
    def test_returns_nested_value(self):
        with patch(
            "apmatia.core.app_config.load_app_config",
            return_value={"llm": {"model_name": "test-model"}},
        ):
            result = app_config.get_config_value("llm", "model_name")
        assert result == "test-model"

    def test_returns_default_when_key_not_found(self):
        with patch("apmatia.core.app_config.load_app_config", return_value={}):
            result = app_config.get_config_value("nonexistent", default="default-value")
        assert result == "default-value"

    def test_returns_default_when_intermediate_key_not_dict(self):
        with patch(
            "apmatia.core.app_config.load_app_config", return_value={"llm": "not-a-dict"}
        ):
            result = app_config.get_config_value("llm", "model_name", default="default-value")
        assert result == "default-value"


class TestSetConfigValue:
    def test_sets_and_saves_value(self):
        with patch("apmatia.core.app_config.load_app_config", return_value={}):
            with patch("apmatia.core.app_config.save_app_config") as mock_save:
                with patch("apmatia.core.app_config._config_file"):
                    result = app_config.set_config_value("llm", "model_name", value="new-model")

        assert result["llm"]["model_name"] == "new-model"
        mock_save.assert_called_once()

    def test_raises_error_when_no_keys_provided(self):
        with pytest.raises(ValueError, match="At least one key is required"):
            app_config.set_config_value(value="value")

    def test_sets_deeply_nested_value(self):
        with patch("apmatia.core.app_config.load_app_config", return_value={}):
            with patch("apmatia.core.app_config.save_app_config") as mock_save:
                with patch("apmatia.core.app_config._config_file"):
                    result = app_config.set_config_value(
                        "llm", "openai_compatible", "base_url", value="http://localhost:8000"
                    )

        assert result["llm"]["openai_compatible"]["base_url"] == "http://localhost:8000"
