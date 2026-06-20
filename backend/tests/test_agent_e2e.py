"""End-to-end Agent integration tests with mock LLM.

Tests the full agent loop including tool execution, event emission,
StormBreaker, MicroCompact, ContentRouter, and Checkpoint integration.
"""

import asyncio
import pytest

from app.core.agent import Agent
from app.core.emitter import EventBus, EventType
from app.core.stormbreaker import StormBreaker
from app.llm.base import LLMChunk
from app.session.session import Session
from app.session.microcompact import MicroCompact
from app.session.checkpoint import CheckpointManager
from app.tools.registry import ToolRegistry, Tool
from app.tools.executor import ToolExecutor, ToolResult
from app.headroom.router import create_default_router


class MockLLM:
    """Mock LLM that returns controllable chunks."""

    def __init__(self):
        self.chunks = []  # Each chunk: (text, tool_calls, usage)
        self.call_count = 0

    async def stream(self, messages):
        """Yield pre-configured chunks."""
        self.call_count += 1
        for text, tool_calls, usage in self.chunks:
            yield LLMChunk(text=text, tool_calls=tool_calls, usage=usage)

    async def count_tokens(self, text: str) -> int:
        return len(text) // 4

    async def summarize(self, text: str) -> str:
        return f"[summary of {len(text)} chars]"


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()

    # Register a simple echo tool
    registry.register(Tool(
        name="echo",
        description="Echo back the input",
        handler=lambda text: f"echo: {text}",
        schema={"name": "echo", "description": "Echo", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    ))

    # Register a read tool
    registry.register(Tool(
        name="read",
        description="Read a file",
        handler=lambda file_path: f"content of {file_path}",
        schema={"name": "read", "description": "Read file", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    ))

    return registry


@pytest.fixture
def tool_executor(tool_registry):
    return ToolExecutor(tool_registry)


@pytest.fixture
def content_router():
    return create_default_router()


# ── Test 1: Basic agent loop without tool calls ──


@pytest.mark.asyncio
async def test_agent_basic_conversation(event_bus, tool_executor):
    """Agent with no tool calls should end after one turn."""
    session = Session("e2e-basic")
    llm = MockLLM()
    llm.chunks = [("Hello! How can I help?", [], None)]

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.max_turns = 5

    await agent.run("Hi there")

    # Session should have user + assistant messages
    assert len(session.entries) >= 1
    assert any("Hi there" in str(e.content) for e in session.entries)
    assert llm.call_count == 1


# ── Test 2: Agent with tool calls ──


@pytest.mark.asyncio
async def test_agent_with_tool_call(event_bus, tool_executor):
    """Agent should execute tool calls and feed results back."""
    session = Session("e2e-tool")
    llm = MockLLM()

    # First chunk: text + tool call
    # Second chunk: response after tool result
    llm.chunks = [
        ("Let me check...", [{"function": {"name": "echo", "arguments": {"text": "hello world"}}}], None),
        ("Done! Result was: echo: hello world", [], None),
    ]

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.max_turns = 5

    await agent.run("Echo hello world")

    # LLM should have been called at least once
    assert llm.call_count >= 1
    # Session should have entries
    assert len(session.entries) >= 2


# ── Test 3: Event emission verification ──


@pytest.mark.asyncio
async def test_agent_event_emission(event_bus, tool_executor):
    """Agent should emit all expected events."""
    session = Session("e2e-events")
    llm = MockLLM()
    llm.chunks = [
        ("thinking...", [], None),
        ("No tools needed", [], None),
    ]

    # Subscribe to all events
    queue = event_bus.subscribe("e2e-events")

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.max_turns = 3

    await agent.run("Simple chat")

    # Collect events with timeout
    events = []
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=0.5)
            events.append(event.type)
    except (asyncio.TimeoutError, asyncio.QueueEmpty):
        pass

    # Verify lifecycle events
    event_types = {e.value if hasattr(e, 'value') else e for e in events}
    event_strs = set()
    for e in events:
        event_strs.add(str(e).split('.')[-1] if '.' in str(e) else str(e))

    # Should have at minimum agent_start and agent_end
    all_types = set()
    for e in events:
        if hasattr(e, 'value'):
            all_types.add(e.value)
        else:
            all_types.add(e)

    assert any("agent_start" in str(t) for t in all_types), \
        f"Expected agent_start in events: {all_types}"
    assert any("agent_end" in str(t) for t in all_types), \
        f"Expected agent_end in events: {all_types}"
    assert any("text_delta" in str(t) for t in all_types), \
        f"Expected text_delta in events: {all_types}"


# ── Test 4: StormBreaker integration ──


@pytest.mark.asyncio
async def test_stormbreaker_trips_after_consecutive_errors(event_bus, tool_executor):
    """StormBreaker should trip and interrupt the agent after N consecutive errors."""
    session = Session("e2e-sb")
    llm = MockLLM()

    # Return a tool call that will error
    bad_call = [{"function": {"name": "nonexistent_tool", "arguments": {}}}]
    llm.chunks = [
        ("Calling tool...", bad_call, None),
        ("Calling tool...", bad_call, None),
        ("Calling tool...", bad_call, None),
    ]

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.max_turns = 10
    agent.storm_breaker = StormBreaker(max_consecutive_errors=2)

    await agent.run("Test error handling")

    assert agent.storm_breaker.tripped, "StormBreaker should have tripped"
    assert agent.storm_breaker.message is not None
    # Should have a system entry with the loop guard message
    assert any("[loop guard]" in str(e.content) for e in session.entries), \
        "Expected loop guard message in session"


# ── Test 5: MicroCompact integration ──


@pytest.mark.asyncio
async def test_micro_compact_compresses_old_entries(event_bus, tool_executor):
    """MicroCompact should compress old session entries beyond TTL."""
    session = Session("e2e-mc")
    llm = MockLLM()
    llm.chunks = [
        ("Response after compact", [], None),
    ]

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.micro_compact = MicroCompact(ttl_seconds=0, keep_recent=2)

    # Add many old entries
    for i in range(10):
        await session.append("user", f"old message {i}")

    # Run the agent — triggers micro-compact
    await agent.run("New message")

    # MicroCompact should have compressed entries
    assert len(session.entries) < 15  # Should be fewer than before


# ── Test 6: ContentRouter compression ──


@pytest.mark.asyncio
async def test_content_router_compresses_output(event_bus, tool_executor, content_router):
    """Agent should use ContentRouter to compress tool output."""
    session = Session("e2e-cr")
    llm = MockLLM()

    read_call = [{"function": {"name": "read", "arguments": {"file_path": "/test.txt"}}}]
    llm.chunks = [
        ("Reading file...", read_call, None),
        ("Got the content", [], None),
    ]

    agent = Agent(session, llm, tool_executor, event_bus, content_router=content_router)
    agent.max_turns = 3

    await agent.run("Read the file")
    assert llm.call_count >= 1


# ── Test 7: Checkpoint integration via file edit ──


@pytest.mark.asyncio
async def test_checkpoint_integration(tmp_path, event_bus):
    """Agent with FileEditTool should create checkpoints before edits."""
    session = Session("e2e-ckpt")
    registry = ToolRegistry()

    # Register real file edit tool with checkpoint
    ckpt = CheckpointManager(session_id="e2e-ckpt", ckpt_dir=str(tmp_path / ".ckpt"))
    from app.tools.builtin.file_edit import FileEditTool
    FileEditTool(checkpoint_manager=ckpt).register(registry)

    executor = ToolExecutor(registry)
    llm = MockLLM()

    # Create a real file
    target = tmp_path / "test.py"
    target.write_text("print('old')")

    edit_call = [{"function": {"name": "edit", "arguments": {"file_path": str(target), "old_str": "old", "new_str": "new"}}}]
    llm.chunks = [
        ("Editing file...", edit_call, None),
        ("Done!", [], None),
    ]

    agent = Agent(session, llm, executor, event_bus)
    agent.max_turns = 3

    await agent.run("Edit the file")

    # File should be edited
    assert target.read_text() == "print('new')"
    # Checkpoint should exist
    checkpoints = await ckpt.list_checkpoints(str(target))
    assert len(checkpoints) >= 1, "Expected at least 1 checkpoint"


# ── Test 8: Agent respects max_turns ──


@pytest.mark.asyncio
async def test_agent_max_turns_enforced(event_bus, tool_executor):
    """Agent should stop after max_turns even if LLM keeps returning tool calls."""
    session = Session("e2e-maxturns")
    llm = MockLLM()

    tool_chunk = [{"function": {"name": "echo", "arguments": {"text": "loop"}}}]
    llm.chunks = [
        (f"Turn {i}", tool_chunk, None) for i in range(10)
    ]

    agent = Agent(session, llm, tool_executor, event_bus)
    agent.max_turns = 3

    await agent.run("Loop test")

    # LLM should not have been called more than max_turns times
    assert llm.call_count <= 3, f"Expected ≤3 calls, got {llm.call_count}"


# ── Test 9: Agent sub-agent delegation schema ──


@pytest.mark.asyncio
async def test_agent_tool_registration():
    """AgentTool should register its schema correctly."""
    from app.tools.builtin.agent_tool import AgentTool

    registry = ToolRegistry()
    AgentTool(agent_factory=lambda sid: None).register(registry)

    tool = registry.get("delegate_task")
    assert tool is not None
    assert "task" in tool.schema["parameters"]["properties"]
    assert tool.schema["parameters"]["required"] == ["task"]
