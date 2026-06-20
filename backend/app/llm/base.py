"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class LLMChunk:
    text: str = ""
    tool_calls: list = field(default_factory=list)
    usage: dict | None = None


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def stream(self, messages: list) -> AsyncGenerator[LLMChunk, None]:
        """Stream a response for the given messages."""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        ...
