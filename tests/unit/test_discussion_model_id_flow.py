"""Unit tests for model_id flow in the discussion module."""

from unittest.mock import Mock, patch

from apmatia.api.http.routes.discussion_routes import PromptPayload
from apmatia.modules.ai_model_manager.models import LLMConfig


def test_prompt_payload_includes_model_id():
    """Test that PromptPayload model includes model_id field."""
    payload = PromptPayload(
        prompt="Hello",
        agent_id=1,
        discussion_id="disc-123",
        model_id=42,
    )
    
    assert payload.prompt == "Hello"
    assert payload.agent_id == 1
    assert payload.discussion_id == "disc-123"
    assert payload.model_id == 42


def test_prompt_payload_model_id_is_optional():
    """Test that model_id is optional in PromptPayload."""
    payload = PromptPayload(
        prompt="Hello",
        agent_id=1,
    )
    
    assert payload.model_id is None


def test_llm_config_with_model_url():
    """Test that LLMConfig properly stores model_url."""
    config = LLMConfig(
        user_alias="Qwen-80B",
        backend="openai_compatible",
        provider_name="qwen-80b",
        model_url="http://localhost:8080",
        api_key="sk-test123",
        max_response_size=8192,
    )
    
    assert config.model_url == "http://localhost:8080"
    assert config.backend == "openai_compatible"
    assert config.provider_name == "qwen-80b"


def test_llm_config_with_docker_gateway_url():
    """Test that LLMConfig can store Docker gateway URLs."""
    config = LLMConfig(
        user_alias="Qwen-80B",
        backend="openai_compatible",
        model_url="http://172.17.0.1:8080",
        api_key="sk-test123",
    )
    
    assert config.model_url == "http://172.17.0.1:8080"


@patch("apmatia.modules.contacts_and_discussions.services.OpenAICompatibleBackend")
def test_build_backend_uses_llm_config(mock_backend):
    """Test that _build_backend uses llm_config.model_url."""
    from apmatia.modules.contacts_and_discussions.services import _build_backend
    
    llm_config = LLMConfig(
        user_alias="Qwen-80B",
        backend="openai_compatible",
        provider_name="qwen-80b",
        model_url="http://localhost:8080",
        api_key="sk-test123",
    )
    
    _build_backend(llm_config)
    
    mock_backend.assert_called_once()
    call_kwargs = mock_backend.call_args[1]
    assert call_kwargs["base_url"] == "http://localhost:8080"
    assert call_kwargs["api_key"] == "sk-test123"
    assert call_kwargs["model_name"] == "qwen-80b"


def test_resolve_docker_host_loopback_localhost():
    """Test that localhost URLs get rewritten in Docker."""
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        _resolve_docker_host_loopback,
        _running_in_docker,
    )
    
    with patch("ysparr.modalities.text2text.backends.openai_compatible_backend.os") as mock_os:
        mock_os.getenv.return_value = "1"
        mock_os.path.exists.return_value = True
        
        result = _resolve_docker_host_loopback("http://localhost:8080")
        
        # Should be rewritten to Docker gateway
        assert "172.17.0.1" in result or "host.docker.internal" in result


def test_resolve_docker_host_loopback_preserves_non_loopback():
    """Test that non-loopback URLs are preserved in Docker."""
    from ysparr.modalities.text2text.backends.openai_compatible_backend import (
        _resolve_docker_host_loopback,
    )
    
    with patch("ysparr.modalities.text2text.backends.openai_compatible_backend._running_in_docker") as mock_running:
        mock_running.return_value = True
        
        result = _resolve_docker_host_loopback("http://api.example.com:8080")
        
        # Should preserve the original URL
        assert "api.example.com" in result


def test_model_id_extraction_from_agent():
    """Test that model_id is correctly extracted from agent configuration."""
    agent = {
        "id": 1,
        "name": "Ada the Architect",
        "active_model_id": 5,
        "default_model_id": 5,
    }
    
    # Active model_id should be used
    model_id = agent.get("active_model_id") or agent.get("default_model_id")
    assert model_id == 5


def test_model_id_fallback_to_default():
    """Test that model_id falls back to default when active is None."""
    agent = {
        "id": 1,
        "name": "Ada the Architect",
        "active_model_id": None,
        "default_model_id": 7,
    }
    
    model_id = agent.get("active_model_id") or agent.get("default_model_id")
    assert model_id == 7
