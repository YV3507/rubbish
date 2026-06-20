"""Agent tool: delegate to a sub-agent (fork)."""

import asyncio
import uuid

from app.tools.registry import Tool, ToolRegistry


class AgentTool:
    """Delegate tasks to a sub-agent with a forked session."""

    def __init__(self, agent_factory):
        self._factory = agent_factory

    async def delegate(self, task: str, session_id: str = "") -> str:
        """Fork a sub-agent to handle the given task."""
        sub_session_id = session_id or f"fork-{uuid.uuid4().hex[:8]}"
        sub_agent = self._factory(sub_session_id)
        asyncio.create_task(sub_agent.run(task))
        return f"Sub-agent started: {sub_session_id}"

    def register(self, registry: ToolRegistry):
        registry.register(
            Tool(
                name="delegate_task",
                description="Delegate a task to a sub-agent",
                handler=self.delegate,
                schema={
                    "name": "delegate_task",
                    "description": "Fork a sub-agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string"},
                            "session_id": {"type": "string"},
                        },
                        "required": ["task"],
                    },
                },
            )
        )
