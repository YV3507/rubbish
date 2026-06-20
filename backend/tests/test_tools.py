"""Tests for tool registry, executor, offload manager, and built-in tools."""

import pytest
from unittest.mock import AsyncMock

from app.tools.registry import Tool, ToolRegistry
from app.tools.executor import ToolExecutor, ToolResult
from app.tools.offload import OffloadManager
from app.tools.builtin.shell import ShellTool


# ── Registry ──

def test_registry_register_and_get():
    """ToolRegistry stores and retrieves tools by name."""
    reg = ToolRegistry()
    handler = AsyncMock(return_value="ok")
    tool = Tool(name="test_tool", description="Test", handler=handler, schema={})
    reg.register(tool)

    assert reg.get("test_tool") is tool


def test_registry_to_openai_schemas():
    """ToolRegistry converts tools to OpenAI function schemas."""
    reg = ToolRegistry()
    reg.register(Tool(name="foo", description="Foo", handler=lambda: None, schema={"name": "foo"}))
    schemas = reg.to_openai_schemas()
    assert any(s["function"]["name"] == "foo" for s in schemas)


# ── Executor ──

@pytest.mark.asyncio
async def test_executor_read_write_partition():
    """ToolExecutor separates read (parallel) and write (serial) tools."""
    reg = ToolRegistry()
    reg.register(Tool(name="read", description="R", handler=AsyncMock(return_value="r"), schema={}))
    reg.register(Tool(name="write", description="W", handler=AsyncMock(return_value="w"), schema={}))

    executor = ToolExecutor(reg, max_concurrent_reads=2)
    calls = [
        {"function": {"name": "read", "arguments": {}}},
        {"function": {"name": "write", "arguments": {}}},
    ]
    results = await executor.execute_parallel(calls)
    assert len(results) == 2
    assert results[0].content == "r"
    assert results[1].content == "w"


@pytest.mark.asyncio
async def test_executor_unknown_tool():
    """Executor returns error for unknown tool."""
    reg = ToolRegistry()
    executor = ToolExecutor(reg)
    results = await executor.execute_parallel(
        [{"function": {"name": "nope", "arguments": {}}}]
    )
    assert "Unknown tool" in results[0].error


# ── OffloadManager ──

@pytest.mark.asyncio
async def test_offload_below_threshold(tmp_path):
    """OffloadManager returns content unchanged when under threshold."""
    om = OffloadManager(storage_dir=str(tmp_path), threshold=100)
    result = await om.store("small content")
    assert result == "small content"


@pytest.mark.asyncio
async def test_offload_above_threshold(tmp_path):
    """OffloadManager stores and returns reference for large content."""
    om = OffloadManager(storage_dir=str(tmp_path), threshold=5)
    large = "x" * 100
    result = await om.store(large)
    assert result.startswith("[offloaded:")

    loaded = await om.load(result)
    assert loaded == large


# ── ShellTool ──

@pytest.mark.asyncio
async def test_shell_tool_timeout():
    """ShellTool returns timeout error when command exceeds limit."""
    tool = ShellTool(timeout=0.001)  # very short
    result = await tool.run("ping 127.0.0.1 -n 10")
    assert "timed out" in result
