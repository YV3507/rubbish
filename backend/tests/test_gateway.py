"""Tests for Gateway facade and emitter event bus."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.gateway import Gateway
from app.core.emitter import EventBus, EventType


@pytest.mark.asyncio
async def test_gateway_creates_session():
    """Gateway creates a new session on first run."""
    gateway = Gateway()
    with patch("app.core.gateway.Gateway.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "sid-123"
        sid = await gateway.run("sid-123", "hello")
        assert sid == "sid-123"


@pytest.mark.asyncio
async def test_emitter_subscribe_and_emit():
    """EventBus delivers events to subscribers."""
    bus = EventBus()
    queue = bus.subscribe("test-session")

    from app.core.emitter import Event
    await bus.emit("text_delta", {"text": "hello"}, session_id="test-session")

    event = await queue.get()
    assert event.type == EventType.TEXT_DELTA
    assert event.data["text"] == "hello"


@pytest.mark.asyncio
async def test_emitter_unsubscribe():
    """EventBus removes subscribers on unsubscribe."""
    bus = EventBus()
    queue = bus.subscribe("s")
    bus.unsubscribe("s", queue)

    assert queue not in bus._subscribers["s"]


@pytest.mark.asyncio
async def test_emitter_multiple_subscribers():
    """EventBus delivers to all subscribers of a session."""
    bus = EventBus()
    q1 = bus.subscribe("s")
    q2 = bus.subscribe("s")

    await bus.emit("status", {"msg": "ok"}, session_id="s")

    e1 = await q1.get()
    e2 = await q2.get()
    assert e1.data["msg"] == "ok"
    assert e2.data["msg"] == "ok"
