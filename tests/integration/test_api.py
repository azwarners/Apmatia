from unittest.mock import patch

from fastapi.testclient import TestClient
from src.api.http.app import app

client = TestClient(app)


@patch("src.api.http.routes.prompt_llm")
def test_api_prompt(mock_prompt_llm):
    mock_prompt_llm.return_value = "mocked api response"

    response = client.get("/api/prompt?prompt=Nick")

    assert response.status_code == 200
    assert response.json() == {"message": "mocked api response"}
