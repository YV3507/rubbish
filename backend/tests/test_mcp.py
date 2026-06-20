"""Tests for MCP manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.registry import ToolRegistry
from app.mcp.manager import MCPManager


@pytest.mark.asyncio
async def test_mcp_manager_init():
    """MCPManager initializes with a registry."""
    reg = ToolRegistry()
    mgr = MCPManager(reg)
    assert mgr._registry is reg


@pytest.mark.asyncio
async def test_mcp_connect_stdio_failure():
    """MCPManager handles missing stdio command gracefully."""
    reg = ToolRegistry()
    mgr = MCPManager(reg)

    with pytest.raises(FileNotFoundError):
        await mgr.connect_stdio("test", "nonexistent-command")


@pytest.mark.asyncio
async def test_mcp_connect_sse():
    """MCPManager connects via SSE and registers tools."""
    reg = ToolRegistry()
    mgr = MCPManager(reg)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tools": [
            {"name": "search", "description": "Search the web", "parameters": {}}
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch.object(mgr._http_client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await mgr.connect_sse("web", "http://mcp-server:8080/mcp")

        assert "web" in mgr._connections
        assert mgr._connections["web"]["type"] == "sse"
        # Tool should be registered
        assert reg.get("web:search") is not None


@pytest.mark.asyncio
async def test_mcp_disconnect_stdio():
    """MCPManager disconnects stdio and terminates process."""
    reg = ToolRegistry()
    mgr = MCPManager(reg)

    mock_proc = MagicMock()
    mock_proc.terminate.return_value = None
    mock_proc.wait = AsyncMock(return_value=0)

    mgr._connections["test"] = {"process": mock_proc, "type": "stdio"}
    await mgr.disconnect("test")
    mock_proc.terminate.assert_called_once()
    assert "test" not in mgr._connections


@pytest.mark.asyncio
async def test_mcp_disconnect_sse():
    """MCPManager disconnects SSE (no process to terminate)."""
    reg = ToolRegistry()
    mgr = MCPManager(reg)

    mgr._connections["test"] = {"url": "http://example.com", "type": "sse"}
    await mgr.disconnect("test")
    assert "test" not in mgr._connections
