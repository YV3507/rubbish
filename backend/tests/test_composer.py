"""Tests for Compose system cache-optimized prompt construction."""

import pytest

from app.llm.composer import Composer


def test_composer_simple_construction():
    """Composer builds messages with static and dynamic parts."""
    c = Composer("You are a helpful assistant.")
    c.add_tools([
        {"name": "read", "description": "Read a file"},
        {"name": "edit", "description": "Edit a file"},
    ])

    messages = c.build("fix the bug")
    assert len(messages) == 3  # system + tools + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert "fix the bug" in messages[-1]["content"]


def test_composer_includes_history():
    """Composer includes history between static and current user message."""
    c = Composer("You are a helper.")
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "response"},
    ]

    messages = c.build("second message", history=history)
    assert len(messages) == 4  # system + user/assistant history + current user
    assert messages[1] == history[0]
    assert messages[2] == history[1]
    assert messages[3]["role"] == "user"


def test_composer_plan_mode_decoration():
    """Compose appends plan mode marker to user message tail."""
    c = Composer("You are a helper.")
    decorated = c.compose_user("fix the bug", plan_mode=True)
    assert "[Plan Mode" in decorated
    assert decorated.endswith("]")


def test_composer_memory_updates():
    """Compose appends memory updates to user message tail."""
    c = Composer("You are a helper.")
    decorated = c.compose_user("hello", memory_updates="user prefers Python")
    assert "<memory-update>" in decorated


def test_composer_cache_fingerprint():
    """Composer detects cache hits/misses correctly."""
    c = Composer("System prompt")
    assert not c.is_cache_hit

    c.build("hello")
    c.mark_cached()
    assert c.is_cache_hit


def test_composer_cache_miss_on_prompt_change():
    """Composer detects cache miss when system prompt changes."""
    c = Composer("System prompt")
    c.build("hello")
    c.mark_cached()

    c.set_system_prompt("New system prompt")
    assert not c.is_cache_hit
