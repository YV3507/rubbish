"""Session — tree of entries with branching support.

Configurable via config.session_soft_limit_bytes.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import config


@dataclass
class Entry:
    role: str  # user, assistant, tool, system
    content: str | list
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class Session:
    """A conversation session with a tree of entries."""

    def __init__(self, session_id: str = ""):
        self.id = session_id or uuid.uuid4().hex
        self.entries: list[Entry] = []
        self.branches: dict[str, list[Entry]] = {}
        self.metadata: dict = {}

    async def append(self, role: str, content: str | list):
        """Append an entry to the session."""
        entry = Entry(role=role, content=content)
        self.entries.append(entry)

    async def build_messages(self) -> list[dict]:
        """Build OpenAI-compatible messages from session entries."""
        messages = []
        for entry in self.entries:
            msg = {"role": entry.role, "content": entry.content}
            messages.append(msg)
        return messages

    @property
    def headroom(self) -> float:
        """Approximate water level (0-1) based on total content length."""
        total = sum(len(str(e.content)) for e in self.entries)
        return min(1.0, total / config.session_soft_limit_bytes)

    async def compact(self):
        """Trigger compaction when water level is high."""
        pass

    def fork(self) -> "Session":
        """Create a forked copy of this session."""
        new = Session(session_id=f"{self.id}-fork")
        new.entries = self.entries.copy()
        return new
