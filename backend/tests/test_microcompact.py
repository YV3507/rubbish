"""Tests for MicroCompact time-aware compression."""

import pytest
from datetime import datetime, timedelta, timezone

from app.session.session import Session, Entry
from app.session.microcompact import MicroCompact


@pytest.mark.asyncio
async def test_microcompact_skips_recent_entries():
    """MicroCompact preserves recent entries within TTL."""
    session = Session()
    mc = MicroCompact(ttl_seconds=3600, keep_recent=1)

    # Add recent entries
    for i in range(3):
        entry = Entry(
            role="tool",
            content=[{"tool_call_id": "read", "content": "old result"}],
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.entries.append(entry)

    # Add very recent entries
    for i in range(2):
        entry = Entry(
            role="tool",
            content=[{"tool_call_id": "grep", "content": "recent result"}],
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        session.entries.append(entry)

    compacted = await mc.compact(session)
    assert compacted == 3  # old entries compacted

    # Check recent entries preserved
    remaining = [
        e for e in session.entries
        if isinstance(e.content, list)
    ]
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_microcompact_keeps_assistant_context():
    """MicroCompact preserves assistant entries and their subsequent tool results."""
    session = Session()
    mc = MicroCompact(ttl_seconds=60, keep_recent=2)

    # Add old compactable tool results
    old_entry = Entry(
        role="tool",
        content=[{"tool_call_id": "shell", "content": "old output"}],
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session.entries.append(old_entry)

    # Add assistant msg that should be preserved
    assist_entry = Entry(
        role="assistant",
        content="Let me check",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    session.entries.append(assist_entry)

    # Add recent tool result after assistant (should be preserved)
    recent_tool = Entry(
        role="tool",
        content=[{"tool_call_id": "read", "content": "recent"}],
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    session.entries.append(recent_tool)

    compacted = await mc.compact(session)
    # Only the old entry (shell) should be compacted
    assert compacted >= 1


@pytest.mark.asyncio
async def test_microcompact_skips_non_compressible():
    """MicroCompact only compresses known tool types."""
    session = Session()
    mc = MicroCompact(ttl_seconds=60, keep_recent=0)

    # These should NOT be compacted (non-standard tool names)
    entry = Entry(
        role="tool",
        content=[{"tool_call_id": "generate_image", "content": "image data"}],
        timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    session.entries.append(entry)

    compacted = await mc.compact(session)
    assert compacted == 0
