"""Tool registry — central registry for all built-in and MCP tools."""

from __future__ import annotations

from typing import Any


class Tool:
    """A registered tool with metadata."""

    def __init__(self, name: str, description: str, handler: callable, schema: dict):
        self.name = name
        self.description = description
        self.handler = handler
        self.schema = schema


class ToolRegistry:
    """Registry that maps tool names to Tool instances."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_schemas(self) -> list[dict]:
        return [{"type": "function", "function": t.schema} for t in self._tools.values()]
