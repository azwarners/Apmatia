from datetime import datetime
from unittest.mock import patch

from src.lib.model_management.models import LLM
from src.lib.model_management.module import LLMManager


def test_list_configs_normalizes_missing_base_fields():
    manager = LLMManager()

    with patch(
        "src.lib.model_management.module.get_config_value",
        return_value=[
            {
                "id": 1,
                "user_alias": "Local",
                "provider_name": "ollama",
                "model_url": "http://localhost:11434",
                "metadata": {},
            }
        ],
    ):
        configs = manager.list_configs()

    assert len(configs) == 1
    assert configs[0].id == 1
    assert configs[0].owner_user_id is None
    assert configs[0].owner_group_id is None
    assert configs[0].mode == 0
    assert isinstance(configs[0].created_at, datetime)
    assert isinstance(configs[0].updated_at, datetime)


def test_create_config_persists_base_fields():
    manager = LLMManager()
    saved = {}

    def fake_save(config):
        saved.update(config)

    with patch("src.lib.model_management.module.get_config_value", return_value=[]), patch(
        "src.lib.model_management.module.load_app_config",
        return_value={"llm": {"configs": []}},
    ), patch("src.lib.model_management.module.save_app_config", side_effect=fake_save):
        created = manager.create_config(
            LLM(
                user_alias="Local",
                provider_name="ollama",
                model_url="http://localhost:11434",
                owner_user_id=7,
            )
        )

    configs = saved["llm"]["configs"]
    assert created.id == 1
    assert created.owner_user_id == 7
    assert len(configs) == 1
    assert configs[0]["owner_user_id"] == 7
    assert configs[0]["owner_group_id"] is None
    assert configs[0]["mode"] == 0
    assert isinstance(configs[0]["created_at"], str)
    assert isinstance(configs[0]["updated_at"], str)


def test_probe_config_uses_limited_prompt_response():
    manager = LLMManager()

    with patch.object(
        manager,
        "list_configs",
        return_value=[
            LLM(
                id=4,
                user_alias="Verifier",
                backend="openai_compatible",
                provider_name="demo",
                model_url="http://localhost:5001",
                max_response_size=4096,
            )
        ],
    ), patch(
        "src.lib.model_management.module.prompt_llm",
        return_value="ready and connected",
    ) as mock_prompt:
        result = manager.probe_config(4)

    assert result["config_id"] == 4
    assert result["user_alias"] == "Verifier"
    assert result["model_url"] == "http://localhost:5001"
    assert result["reply_preview"] == "ready and connected"
    probed_config = mock_prompt.call_args.kwargs["llm_config"]
    assert probed_config.max_response_size == 64
