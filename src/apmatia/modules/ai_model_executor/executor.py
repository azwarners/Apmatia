from __future__ import annotations

import logging
from typing import Any

import httpx

from apmatia.modules.ai_model_executor.models import WorkItem, TextGenerationWorkPayload

logger = logging.getLogger(__name__)


class ExecutorService:
    """
    Executes WorkItems by calling the appropriate ModelRuntime endpoint.
    Each work item carries a payload with the model_id and prompt; the
    executor resolves the endpoint URL from the runtime repository.
    """

    def __init__(self, runtime_repository, http_client: httpx.AsyncClient | None = None):
        self.repo = runtime_repository
        self._client = http_client

    async def execute(self, work_item: WorkItem) -> dict[str, Any]:
        """
        Run a single WorkItem against its target runtime.

        Returns a dict with keys:
            - status: "completed"
            - model_id: int
            - prompt: str
            - response: str  (the model's generated text)
        """
        if work_item.payload is None:
            raise ValueError("WorkItem has no payload")

        runtime_id = work_item.runtime_id or "llama_cpp"
        runtime = self.repo.get_runtime(runtime_id)
        if not runtime:
            raise ValueError(f"Runtime '{runtime_id}' not found")

        endpoint = runtime.endpoint_url
        if not endpoint:
            raise ValueError(f"Runtime '{runtime_id}' has no endpoint_url")

        payload = work_item.payload
        body = {
            "prompt": payload.prompt,
            "model_id": payload.model_id,
        }
        if payload.system_prompt:
            body["system_prompt"] = payload.system_prompt
        if payload.max_tokens is not None:
            body["max_tokens"] = payload.max_tokens
        if payload.temperature is not None:
            body["temperature"] = payload.temperature

        async with self._client or httpx.AsyncClient() as client:
            resp = await client.post(
                f"{endpoint}/v1/chat/completions",
                json={"messages": [{"role": "user", "content": payload.prompt}], **body},
                timeout=300.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract the generated text from the OpenAI-compatible response
        choices = data.get("choices")
        if not choices:
            logger.warning("Runtime returned no choices for work_item=%s", work_item.id)
            return {
                "status": "completed",
                "model_id": payload.model_id,
                "prompt": payload.prompt,
                "response": "",
            }

        message = choices[0].get("message", {})
        generated = message.get("content", "") or ""

        return {
            "status": "completed",
            "model_id": payload.model_id,
            "prompt": payload.prompt,
            "response": generated,
        }
