from unittest.mock import patch

from src.interfaces.cli.main import main


@patch("src.interfaces.cli.main.prompt_llm")
@patch("sys.argv", ["main.py", "Nick"])
def test_cli_with_prompt(mock_prompt_llm):
    mock_prompt_llm.return_value = "mocked cli response"
    main()
    mock_prompt_llm.assert_called_once_with("Nick", output_dir=None)
