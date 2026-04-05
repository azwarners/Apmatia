from unittest.mock import patch

from src.core.prompt_LLM import prompt_llm


@patch("src.core.prompt_LLM.KoboldCppBackend")
def test_core_prompt(mock_backend_class):
    mock_backend = mock_backend_class.return_value
    mock_backend.stream.return_value = ["chunk one", "chunk two"]

    result = prompt_llm("Nick test")

    assert result == "chunk one\nchunk two"
    mock_backend.stream.assert_called_once()
