"""OpenAI-compatible provider (DeepSeek, MiMo, OpenAI)."""

from typing import AsyncGenerator

import httpx

from app.llm.base import LLMChunk, LLMProvider


class DeepSeekProvider(LLMProvider):
    """Provider for DeepSeek / OpenAI-compatible APIs."""

    PROMPT_CACHE_BLOCK_SIZE = 128

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
        self.cached_system_prompt = ""

    async def stream(self, messages: list) -> AsyncGenerator[LLMChunk, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    yield LLMChunk(
                        text=delta.get("content", ""),
                        tool_calls=delta.get("tool_calls", []),
                        usage=data.get("usage"),
                    )

    async def count_tokens(self, text: str) -> int:
        # Rough estimation; replace with tiktoken in production
        return len(text) // 4
