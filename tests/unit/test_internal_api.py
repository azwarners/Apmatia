from unittest.mock import patch

from src.api.internal.prompt_LLM import prompt_llm


@patch("src.api.internal.prompt_LLM.core_prompt_llm")
def test_internal_prompt(mock_core_prompt):
    mock_core_prompt.return_value = "mocked response"

    result = prompt_llm("Nick test")

    assert result == "mocked response"
    mock_core_prompt.assert_called_once_with("Nick test")
