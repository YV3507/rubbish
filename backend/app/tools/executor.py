"""Tool executor with read/write partition and semaphore-based concurrency.

Uses config.tool_max_concurrent_reads for the read semaphore limit.
"""

import asyncio
from dataclasses import dataclass

from app.config import config


@dataclass
class ToolResult:
    content: str
    tool_call_id: str = ""
    error: str | None = None


class ToolExecutor:
    """Partitioned executor: read tools run in parallel, write tools are serialized."""

    READ_TOOLS = {"read", "glob", "grep", "search"}
    WRITE_TOOLS = {"write", "edit", "delete"}

    def __init__(self, registry, max_concurrent_reads: int | None = None):
        self._registry = registry
        max_reads = max_concurrent_reads or config.tool_max_concurrent_reads
        self._read_sem = asyncio.Semaphore(max_reads)
        self._write_lock = asyncio.Lock()

    async def execute_parallel(self, tool_calls: list) -> list[ToolResult]:
        """Execute tool calls respecting read/write partitioning."""
        tasks = []
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            if name in self.WRITE_TOOLS:
                tasks.append(self._execute_serial(tc))
            else:
                tasks.append(self._execute_read(tc))
        return await asyncio.gather(*tasks)

    async def _execute_read(self, tc) -> ToolResult:
        async with self._read_sem:
            return await self._execute(tc)

    async def _execute_serial(self, tc) -> ToolResult:
        async with self._write_lock:
            return await self._execute(tc)

    async def _execute(self, tc) -> ToolResult:
        name = tc.get("function", {}).get("name", "")
        args = tc.get("function", {}).get("arguments", {})
        tool = self._registry.get(name)
        if not tool:
            return ToolResult(content="", error=f"Unknown tool: {name}")
        try:
            result = await tool.handler(**args)
            return ToolResult(content=str(result))
        except Exception as e:
            return ToolResult(content="", error=str(e))
