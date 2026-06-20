"""Tests for LLM providers, fallback chain, cache alignment, and router."""

import pytest

from app.llm.router import Router
from app.llm.cache_alignment import CacheAlignment


class MockProvider:
    def __init__(self, name: str):
        self.name = name

    async def stream(self, messages):
        yield type("Chunk", (), {"text": f"from {self.name}", "tool_calls": []})


@pytest.mark.asyncio
async def test_router_selects_fast_for_short():
    """Router picks fast provider for short prompts."""
    fast = MockProvider("fast")
    slow = MockProvider("slow")
    router = Router(fast, slow)

    selected = router.select([{"role": "user", "content": "hi"}])
    assert selected.name == "fast"


@pytest.mark.asyncio
async def test_router_selects_reasoning_for_long():
    """Router picks reasoning provider for long prompts."""
    fast = MockProvider("fast")
    slow = MockProvider("slow")
    router = Router(fast, slow)

    long_content = "long " * 2000
    selected = router.select([{"role": "user", "content": long_content}])
    assert selected.name == "slow"


def test_cache_alignment_split():
    """CacheAlignment correctly separates static and dynamic messages."""
    ca = CacheAlignment()
    msgs = [
        {"role": "system", "content": "you are helpful"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    static, dynamic = ca.split_boundary(msgs)
    assert len(static) == 1
    assert len(dynamic) == 2


def test_cache_alignment_fingerprint():
    """CacheAlignment fingerprint changes when system content changes."""
    ca = CacheAlignment()
    msgs_a = [{"role": "system", "content": "prompt A"}]
    msgs_b = [{"role": "system", "content": "prompt B"}]

    fp_a = ca.fingerprint(msgs_a)
    fp_b = ca.fingerprint(msgs_b)
    assert fp_a != fp_b


def test_cache_hit_detection():
    """is_cache_hit returns True only when system content matches."""
    ca = CacheAlignment()
    msgs = [{"role": "system", "content": "same prompt"}]

    assert not ca.is_cache_hit(msgs)
    ca.mark_cached(msgs)
    assert ca.is_cache_hit(msgs)
