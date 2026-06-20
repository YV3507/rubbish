"""MCP client manager: connect to MCP servers via SSE or stdio."""

import asyncio
import json
from pathlib import Path

import httpx

from app.tools.registry import Tool, ToolRegistry


class MCPManager:
    """Manage MCP server connections and dynamically register tools."""

    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._connections: dict[str, dict] = {}
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def connect_stdio(self, name: str, command: str, args: list[str] = None):
        """Connect to an MCP server via stdio transport."""
        proc = await asyncio.create_subprocess_exec(
            command,
            *(args or []),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._connections[name] = {"process": proc, "type": "stdio"}

        # Register exposed tools dynamically
        tool_list = await self._request_stdio(proc, "tools/list")
        for tool_def in tool_list.get("tools", []):
            self._registry.register(
                Tool(
                    name=f"{name}:{tool_def['name']}",
                    description=tool_def.get("description", ""),
                    handler=lambda **kw: self._call_mcp_stdio(proc, tool_def["name"], kw),
                    schema=tool_def,
                )
            )

    async def connect_sse(self, name: str, url: str):
        """Connect to an MCP server via SSE transport.

        Uses HTTP POST for JSON-RPC requests (SSE endpoint for server-sent events).
        """
        self._connections[name] = {"url": url, "type": "sse"}

        # Discover available tools via HTTP POST
        tool_list = await self._request_http(url, "tools/list")
        for tool_def in tool_list.get("tools", []):
            self._registry.register(
                Tool(
                    name=f"{name}:{tool_def['name']}",
                    description=tool_def.get("description", ""),
                    handler=lambda **kw: self._call_mcp_http(url, tool_def["name"], kw),
                    schema=tool_def,
                )
            )

    async def disconnect(self, name: str):
        """Disconnect from an MCP server."""
        conn = self._connections.pop(name, None)
        if conn and conn["type"] == "stdio":
            proc = conn["process"]
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()

    async def _request_stdio(self, proc, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request to MCP server via stdio."""
        req = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1})
        proc.stdin.write(req.encode() + b"\n")
        await proc.stdin.drain()
        response = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
        return json.loads(response)

    async def _request_http(self, url: str, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request to MCP server via HTTP POST."""
        resp = await self._http_client.post(
            url,
            json={"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1},
        )
        resp.raise_for_status()
        return resp.json()

    async def _call_mcp_stdio(self, proc, tool_name: str, args: dict) -> str:
        result = await self._request_stdio(proc, "tools/call", {"name": tool_name, "arguments": args})
        return json.dumps(result)

    async def _call_mcp_http(self, url: str, tool_name: str, args: dict) -> str:
        result = await self._request_http(url, "tools/call", {"name": tool_name, "arguments": args})
        return json.dumps(result)
