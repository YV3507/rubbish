"""Tests for Background Task Manager."""

import asyncio
import time
import pytest

from app.core.background import TaskManager


@pytest.mark.asyncio
async def test_task_manager_start():
    """Start a task and verify it is active."""
    mgr = TaskManager()
    task = mgr.start("session-1")
    assert task.id.startswith("bg-")
    assert task.session_id == "session-1"
    assert task.status == "running"
    assert mgr.list_active() == [task]


@pytest.mark.asyncio
async def test_task_manager_complete():
    """Complete a task and verify status change."""
    mgr = TaskManager()
    task = mgr.start("session-1")

    mgr.complete(task.id)
    assert task.status == "completed"
    assert task.finished_at is not None
    assert mgr.list_active() == []


@pytest.mark.asyncio
async def test_task_manager_complete_with_error():
    """Complete a task with error marks it as failed."""
    mgr = TaskManager()
    task = mgr.start("session-1")

    mgr.complete(task.id, error="timeout")
    assert task.status == "failed"
    assert task.error == "timeout"


@pytest.mark.asyncio
async def test_task_manager_cancel():
    """Cancel a running task."""
    mgr = TaskManager()
    task = mgr.start("session-1")

    result = mgr.cancel(task.id)
    assert result is True
    assert task.status == "cancelled"
    assert task.cancelled is True
    assert mgr.list_active() == []


@pytest.mark.asyncio
async def test_task_manager_cancel_nonexistent():
    """Cancel nonexistent task returns False."""
    mgr = TaskManager()
    result = mgr.cancel("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_task_manager_get():
    """Get task by ID."""
    mgr = TaskManager()
    task = mgr.start("session-1")

    fetched = mgr.get(task.id)
    assert fetched is task

    nonexistent = mgr.get("nonexistent")
    assert nonexistent is None


@pytest.mark.asyncio
async def test_task_manager_list_all():
    """List all tasks includes completed ones."""
    mgr = TaskManager()
    t1 = mgr.start("s1")
    t2 = mgr.start("s2")

    mgr.complete(t2.id)

    all_tasks = mgr.list_all()
    assert len(all_tasks) == 2
    active_tasks = mgr.list_active()
    assert len(active_tasks) == 1
    assert active_tasks[0].id == t1.id


@pytest.mark.asyncio
async def test_task_manager_cleanup():
    """Cleanup removes old completed tasks."""
    mgr = TaskManager()
    task = mgr.start("session-1")
    mgr.complete(task.id)

    # Set finished_at far in the past
    task.finished_at = time.time() - 10000

    mgr.cleanup_completed(max_age_seconds=1)
    assert mgr.get(task.id) is None


@pytest.mark.asyncio
async def test_task_manager_cancel_event():
    """Cancelled task's _cancel_event is set."""
    mgr = TaskManager()
    task = mgr.start("session-1")

    mgr.cancel(task.id)
    assert task._cancel_event.is_set()
