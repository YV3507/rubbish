"""MicroCompact: time-aware compression layer aligned with LLM cache TTL.

Aligns with Anthropic's 5-minute prompt caching TTL:
when the server-side cache has gone cold, locally compact old tool results
without causing additional cache misses.

Reference: Firefly pkg/agent/microcompact.go
"""

from datetime import datetime, timedelta, timezone
from app.session.session import Entry, Session
from app.config import config

# Tool types whose results are safe to replace with ref stubs
COMPRESSIBLE_TOOLS = {"read", "grep", "glob", "shell", "fetch", "edit", "write"}


class MicroCompact:
    """Replace old tool results with compact refs when cache has likely expired."""

    def __init__(
        self,
        ttl_seconds: int | None = None,
        keep_recent: int | None = None,
    ):
        self._ttl = timedelta(
            seconds=ttl_seconds or config.microcompact_ttl_seconds
        )
        self._keep_recent = keep_recent or config.microcompact_keep_recent

    async def compact(self, session: Session) -> int:
        """Run micro-compaction on session entries.

        Returns number of entries compacted.
        """
        now = datetime.now(timezone.utc)
        compacted = 0
        recent_count = 0

        # Walk backwards to identify recent entries to preserve
        preserved_ids: set[str] = set()
        for entry in reversed(session.entries):
            if entry.role == "assistant":
                if len(preserved_ids) >= self._keep_recent:
                    break
                preserved_ids.add(entry.id)
                # Also preserve the next tool entries after this assistant msg
                idx = len(session.entries) - 1 - session.entries[::-1].index(entry)
                for j in range(idx + 1, min(idx + 10, len(session.entries))):
                    if session.entries[j].role == "tool":
                        preserved_ids.add(session.entries[j].id)

        for entry in session.entries:
            if entry.id in preserved_ids:
                continue
            if entry.role != "tool":
                continue
            # Check if the entry content looks like a tool result (list of ToolResult)
            if not isinstance(entry.content, list):
                continue

            age = now - entry.timestamp
            if age < self._ttl:
                continue  # Cache still warm, skip

            # Compact: replace full content with placeholder
            tool_names = self._extract_tool_names(entry.content)
            if tool_names and all(t in COMPRESSIBLE_TOOLS for t in tool_names):
                entry.content = (
                    f"[microcompact: {len(tool_names)} tool(s) — "
                    f"{', '.join(tool_names)} — cache cold at age {age.total_seconds():.0f}s]"
                )
                compacted += 1

        return compacted

    def _extract_tool_names(self, content: list) -> list[str]:
        """Extract tool names from a list of tool result entries."""
        names: list[str] = []
        for item in content:
            if isinstance(item, dict):
                names.append(item.get("tool_call_id", item.get("name", "unknown")))
            elif hasattr(item, "tool_call_id"):
                names.append(getattr(item, "tool_call_id", "unknown"))
        return names
