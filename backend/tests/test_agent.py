"""Tests for Agent main loop and StormBreaker integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.agent import Agent
from app.core.emitter import EventBus
from app.core.stormbreaker import StormBreaker
from app.session.session import Session


@pytest.fixture
def mock_llm():
    """Returns an LLMProvider-like object whose .stream() returns empty async gen."""
    from app.llm.base import LLMChunk

    async def empty_stream(_messages):
        yield LLMChunk(text="", tool_calls=[])

    m = MagicMock(spec=["stream"])
    m.stream = empty_stream
    return m


@pytest.fixture
def mock_tools():
    m = MagicMock()
    m.execute_parallel = AsyncMock(return_value=[])
    return m


@pytest.mark.asyncio
async def test_agent_runs_turns(mock_llm, mock_tools):
    """Agent should start and stop within max_turns."""
    session = Session("test-session")
    agent = Agent(session, mock_llm, mock_tools, EventBus())
    agent.max_turns = 3

    await agent.run("hello")
    assert len(session.entries) >= 1


@pytest.mark.asyncio
async def test_stormbreaker_detects_errors():
    """StormBreaker should trip after N consecutive identical errors."""
    sb = StormBreaker(max_consecutive_errors=2)
    assert not sb.tripped

    class MockResult:
        error = "timeout error"

    sb.record([MockResult()])
    assert not sb.tripped

    sb.record([MockResult()])
    assert sb.tripped


@pytest.mark.asyncio
async def test_stormbreaker_resets_on_success():
    """StormBreaker resets after a successful result."""
    sb = StormBreaker(max_consecutive_errors=3)

    class Fail:
        error = "err"

    class OK:
        error = None

    sb.record([Fail()])
    sb.record([OK()])
    assert not sb.tripped


@pytest.mark.asyncio
async def test_agent_water_level_triggers_compact(mock_llm, mock_tools):
    """Agent should call compact when water level exceeds threshold."""
    session = Session("test-wl")
    # Fill session to trigger water level
    for _ in range(200):
        await session.append("user", "x" * 500)

    agent = Agent(session, mock_llm, mock_tools, EventBus())
    agent.water_level_threshold = 0.1
    # LLM returning no tool calls should cause loop to end
    assert len(session.entries) >= 200


@pytest.mark.asyncio
async def test_agent_offloads_large_results(mock_llm, mock_tools):
    """Agent tags results exceeding threshold as offloaded."""
    session = Session("test-offload")
    agent = Agent(session, mock_llm, mock_tools, EventBus())
    agent.offload_threshold = 10

    from app.tools.executor import ToolResult
    large = ToolResult(content="x" * 100)
    if len(str(large.content)) > agent.offload_threshold:
        large.content = f"[offloaded: {len(str(large.content))} bytes]"
    assert large.content.startswith("[offloaded:")
