from unittest.mock import MagicMock, patch

import pytest

from apmatia.api.internal import agent_prompts


def test_get_compiled_agent_prompt_uses_prompt_id_and_name():
    mock_prompt = object()
    mock_manager = MagicMock()
    mock_manager.get_prompt.return_value = mock_prompt
    mock_manager.compile_agent_system_prompt.return_value = "compiled prompt"

    with patch("apmatia.api.internal.agent_prompts.get_agent_manager", return_value=mock_manager):
        result = agent_prompts.get_compiled_agent_prompt(7, name="Planner")

    assert result == "compiled prompt"
    mock_manager.get_prompt.assert_called_once_with(7)
    mock_manager.compile_agent_system_prompt.assert_called_once_with("Planner", mock_prompt)


def test_get_compiled_agent_prompt_raises_for_missing_prompt():
    mock_manager = MagicMock()
    mock_manager.get_prompt.return_value = None

    with patch("apmatia.api.internal.agent_prompts.get_agent_manager", return_value=mock_manager):
        with pytest.raises(ValueError, match="Agent prompt not found: 7"):
            agent_prompts.get_compiled_agent_prompt(7)
