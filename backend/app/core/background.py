"""Background Task Manager: track and manage long-running agent tasks.

Supports spawning background agent runs, listing active tasks,
and cancellation via asyncio Event.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class BackgroundTask:
    """A tracked background agent task."""
    id: str
    session_id: str
    status: str = "running"  # running | completed | failed | cancelled
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def cancel(self):
        """Signal cancellation for this task."""
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()


class TaskManager:
    """Manage background agent tasks with lifecycle tracking."""

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}

    def start(self, session_id: str) -> BackgroundTask:
        """Register a new background task and return its metadata."""
        task_id = f"bg-{uuid.uuid4().hex[:12]}"
        task = BackgroundTask(id=task_id, session_id=session_id)
        self._tasks[task_id] = task
        return task

    def complete(self, task_id: str, error: str | None = None):
        """Mark a task as completed (or failed if error is provided)."""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.finished_at = time.time()
        task.status = "failed" if error else "completed"
        task.error = error

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task by ID. Returns True if found."""
        task = self._tasks.get(task_id)
        if not task or task.status != "running":
            return False
        task.cancel()
        task.status = "cancelled"
        task.finished_at = time.time()
        return True

    def get(self, task_id: str) -> BackgroundTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_active(self) -> list[BackgroundTask]:
        """Return all currently running tasks."""
        return [t for t in self._tasks.values() if t.status == "running"]

    def list_all(self) -> list[BackgroundTask]:
        """Return all tracked tasks."""
        return list(self._tasks.values())

    def cleanup_completed(self, max_age_seconds: float = 3600):
        """Remove completed tasks older than max_age_seconds."""
        now = time.time()
        to_remove = [
            tid for tid, t in self._tasks.items()
            if t.status != "running"
            and t.finished_at is not None
            and (now - t.finished_at) > max_age_seconds
        ]
        for tid in to_remove:
            del self._tasks[tid]
