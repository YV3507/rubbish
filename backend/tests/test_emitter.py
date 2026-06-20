"""Tests for enhanced EventBus with AgentEmitter."""

import asyncio
import pytest

from app.core.emitter import EventBus, AgentEmitter, EventType


@pytest.mark.asyncio
async def test_eventbus_subscribe_kind_filter():
    """Subscribe with kind filter only receives matching events."""
    bus = EventBus()
    queue = bus.subscribe("test", kind="text_delta")

    await bus.emit("text_delta", {"text": "hello"}, session_id="test")
    await bus.emit("status", {"msg": "ok"}, session_id="test")

    received = await asyncio.wait_for(queue.get(), timeout=1)
    assert received.type == EventType.TEXT_DELTA

    # Status events should not arrive on this queue
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_agent_emitter_injects_source():
    """AgentEmitter auto-injects agent name into events."""
    bus = EventBus()
    queue = bus.subscribe("test")

    emitter = AgentEmitter(bus, agent_name="main")
    emitter.bind_session("test")
    await emitter.emit("text_delta", {"text": "hi"})

    received = await asyncio.wait_for(queue.get(), timeout=1)
    assert received.source == "main"
    assert received.data.get("agent") == "main"


@pytest.mark.asyncio
async def test_eventbus_wildcard_subscribe():
    """Wildcard subscription receives all event types."""
    bus = EventBus()
    queue = bus.subscribe("test")  # kind=None → "*"

    await bus.emit("text_delta", {}, session_id="test")
    await bus.emit("status", {}, session_id="test")
    await bus.emit("error", {}, session_id="test")

    for _ in range(3):
        event = await asyncio.wait_for(queue.get(), timeout=1)
        assert event is not None
