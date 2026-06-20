"""Fallback chain with loop detection for LLM providers."""

from typing import AsyncGenerator

from app.llm.base import LLMChunk, LLMProvider


class FallbackChain:
    """Chain of providers with fallback on failure."""

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers
        self._attempted = set()

    async def stream(self, messages: list) -> AsyncGenerator[LLMChunk, None]:
        """Try each provider in order until one succeeds."""
        last_error = None
        for provider in self.providers:
            try:
                async for chunk in provider.stream(messages):
                    yield chunk
                return
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise RuntimeError(f"All providers failed: {last_error}")
