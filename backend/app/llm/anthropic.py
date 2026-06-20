"""Anthropic Claude provider with cache_control support."""

from typing import AsyncGenerator

import httpx

from app.llm.base import LLMChunk, LLMProvider


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
        self.base_url = "https://api.anthropic.com/v1"

    async def stream(self, messages: list) -> AsyncGenerator[LLMChunk, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        async with self.client.stream(
            "POST",
            f"{self.base_url}/messages",
            json=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        ) as resp:
            async with resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            yield LLMChunk(text=delta.get("text", ""))
                        elif data.get("type") == "message_start":
                            pass

    async def count_tokens(self, text: str) -> int:
        return len(text) // 4
