"""Thin asynchronous client for the standalone Ysparr service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx


class YsparrClientError(RuntimeError):
    """A request to the external Ysparr service failed."""


class YsparrClient:
    """Submit OpenAI-compatible requests without importing Ysparr internals."""

    def __init__(self, base_url: str, api_key: str | None = None, transport=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def models(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/models")

    async def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/chat/completions", payload)

    async def cancel(self, job_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/ysparr/v1/jobs/{job_id}")

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                response = await client.request(method, f"{self.base_url}{path}", json=payload, headers=self._headers())
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise YsparrClientError("Ysparr request failed") from exc
        if not isinstance(result, dict):
            raise YsparrClientError("Ysparr returned an invalid response")
        return result

    async def stream(self, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        """Yield SSE bytes as they arrive from Ysparr."""
        try:
            async with httpx.AsyncClient(timeout=None, transport=self.transport) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/v1/chat/completions", json={**payload, "stream": True}, headers=self._headers()
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except httpx.HTTPError as exc:
            raise YsparrClientError("Ysparr streaming request failed") from exc
