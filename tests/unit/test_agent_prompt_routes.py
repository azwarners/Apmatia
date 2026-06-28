from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.http.routes import agent_prompt_routes


def test_get_compiled_prompt_uses_prompt_id_and_name():
    with patch(
        "src.api.http.routes.agent_prompt_routes.get_compiled_agent_prompt",
        return_value="compiled prompt",
    ) as mock_get_compiled:
        result = agent_prompt_routes.get_compiled_prompt(17, name="Planner")

    assert result == "compiled prompt"
    mock_get_compiled.assert_called_once_with(17, name="Planner")


def test_get_compiled_prompt_returns_404_for_missing_prompt():
    with patch(
        "src.api.http.routes.agent_prompt_routes.get_compiled_agent_prompt",
        side_effect=ValueError("Agent prompt not found: 17"),
    ):
        with pytest.raises(HTTPException) as error:
            agent_prompt_routes.get_compiled_prompt(17, name="Planner")

    assert error.value.status_code == 404
    assert error.value.detail == "Agent prompt not found: 17"
