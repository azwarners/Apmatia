from types import SimpleNamespace
from unittest.mock import patch

from apmatia.modules.contacts_and_discussions.services import prompt_llm


@patch("apmatia.modules.contacts_and_discussions.services.KoboldCppBackend")
@patch("apmatia.modules.contacts_and_discussions.services.TextFileStorage")
@patch("apmatia.modules.contacts_and_discussions.services.execute")
def test_core_prompt(mock_execute, mock_storage_class, mock_backend_class, tmp_path):
    output_file = tmp_path / "output.txt"
    output_file.write_text("chunk one\nchunk two", encoding="utf-8")
    mock_execute.return_value = SimpleNamespace(output_path=str(output_file))

    result = prompt_llm("Nick test", output_dir="/tmp/apmatia_logs")

    assert result == "chunk one\nchunk two"
    mock_storage_class.assert_called_once_with("/tmp/apmatia_logs")
    mock_execute.assert_called_once()
