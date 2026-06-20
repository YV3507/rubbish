"""Tests for session, checkpoint, and compactor."""

import pytest

from app.session.session import Session, Entry
from app.session.checkpoint import CheckpointManager
from app.session.compactor import Compactor


@pytest.mark.asyncio
async def test_session_append_and_build():
    """Session correctly appends entries and builds messages."""
    session = Session("test")
    await session.append("user", "hello")
    await session.append("assistant", "world")

    msgs = await session.build_messages()
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "hello"}
    assert msgs[1] == {"role": "assistant", "content": "world"}


@pytest.mark.asyncio
async def test_session_headroom():
    """Session headroom increases with content length."""
    session = Session()
    assert session.headroom == 0.0

    await session.append("user", "x" * 50_000)
    assert session.headroom > 0.0
    assert session.headroom <= 1.0


def test_session_fork():
    """Session fork creates an independent copy."""
    s1 = Session("orig")
    s1.entries.append(Entry(role="user", content="hello"))
    s2 = s1.fork()

    assert s2.id != s1.id
    assert len(s2.entries) == len(s1.entries)


@pytest.mark.asyncio
async def test_compactor_stays_below_budget():
    """Compactor does nothing when under token budget."""
    session = Session()
    for _ in range(10):
        await session.append("user", "short msg")

    compactor = Compactor()
    entries_before = len(session.entries)
    await compactor.compact(session)
    assert len(session.entries) == entries_before


# ── Checkpoint ──

@pytest.mark.asyncio
async def test_checkpoint_save_and_rollback(tmp_path):
    """Checkpoint manager saves snapshots and restores them."""
    target = tmp_path / "test.txt"
    target.write_text("original content")

    cm = CheckpointManager(session_id="test", ckpt_dir=str(tmp_path))
    await cm.save(str(target), "original content")

    target.write_text("modified content")
    rolled = await cm.rollback(str(target))

    assert rolled == "original content"
    assert target.read_text() == "original content"


@pytest.mark.asyncio
async def test_checkpoint_list_filtered(tmp_path):
    """Checkpoint listing filters by file path."""
    cm = CheckpointManager(session_id="test", ckpt_dir=str(tmp_path))
    await cm.save("/a.txt", "a")
    await cm.save("/b.txt", "b")

    all_cps = await cm.list_checkpoints()
    assert len(all_cps) == 2

    filtered = await cm.list_checkpoints("/a.txt")
    assert len(filtered) == 1
