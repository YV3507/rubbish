"""Event bus: publish/subscribe for 39+ event types using asyncio.Queue.

Supports kind-based filtering (subscribe to specific event types)
and automatic agent source injection.

Reference: Firefly pkg/message/ (Bus interface + agentEmitter)
"""

import asyncio
from enum import Enum
from typing import Any


class EventType(str, Enum):
    # Text streaming
    TEXT_DELTA = "text_delta"
    TEXT_DONE = "text_done"

    # Tool lifecycle
    TOOL_CALL = "tool_call"
    TOOL_EXEC_START = "tool_exec_start"
    TOOL_EXEC_END = "tool_exec_end"
    TOOL_RESULT = "tool_result"

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_STATUS = "agent_status"

    # Planning
    PLAN_START = "plan_start"
    PLAN_STEP = "plan_step"
    PLAN_DONE = "plan_done"

    # Sub-agent
    SUB_AGENT_SPAWN = "sub_agent_spawn"
    SUB_AGENT_RESULT = "sub_agent_result"

    # Compression
    COMPACT_START = "compact_start"
    COMPACT_END = "compact_end"
    MICRO_COMPACT = "micro_compact"

    # Permission
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_RESULT = "permission_result"

    # Error / interrupt
    ERROR = "error"
    INTERRUPT = "interrupt"

    # Status / metrics
    STATUS = "status"
    USAGE = "usage"
    CACHE_METRIC = "cache_metric"

    # Background tasks
    BACKGROUND_START = "background_start"
    BACKGROUND_END = "background_end"


class Event:
    """A structured event with type, data, and optional source."""

    def __init__(self, type: EventType, data: dict, source: str = "system"):
        self.type = type
        self.data = data
        self.source = source


class EventBus:
    """Async event bus with kind-based filtering support."""

    def __init__(self):
        self._subscribers: dict[str, dict[str, list[asyncio.Queue]]] = {}

    def subscribe(self, session_id: str, kind: str | None = None) -> asyncio.Queue:
        """Subscribe to events for a session.

        If kind is specified, only events of that type will be delivered.
        """
        queue: asyncio.Queue = asyncio.Queue()
        session_subs = self._subscribers.setdefault(session_id, {})
        session_subs.setdefault(kind or "*", []).append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        session_subs = self._subscribers.get(session_id, {})
        for kind_key in list(session_subs.keys()):
            if queue in session_subs[kind_key]:
                session_subs[kind_key].remove(queue)

    async def emit(
        self,
        event_type: str,
        data: dict | Any = None,
        session_id: str = "default",
        source: str = "system",
    ):
        """Emit an event to all matching subscribers."""
        event = Event(EventType(event_type), data or {}, source)
        session_subs = self._subscribers.get(session_id, {})

        # Deliver to wildcard subscribers and specific-kind subscribers
        targets = list(session_subs.get("*", [])) + list(session_subs.get(event_type, []))

        for queue in targets:
            await queue.put(event)


class AgentEmitter:
    """Agent-scoped emitter that auto-injects source field.

    Wraps an EventBus and prefixes each event with the agent's name.
    This allows frontend to distinguish main agent events from sub-agent events.

    Reference: Firefly pkg/agent/emitter.go
    """

    def __init__(self, bus: EventBus, agent_name: str = "main"):
        self._bus = bus
        self._agent_name = agent_name
        self._session_id = "default"

    def bind_session(self, session_id: str):
        """Bind this emitter to a specific session."""
        self._session_id = session_id

    async def emit(self, event_type: str, data: dict | Any = None):
        """Emit with auto-injected source."""
        enriched = {
            "agent": self._agent_name,
            **(data or {}),
        }
        await self._bus.emit(
            event_type=event_type,
            data=enriched,
            session_id=self._session_id,
            source=self._agent_name,
        )
