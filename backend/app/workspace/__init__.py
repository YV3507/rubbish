"""Workspace model and manager — tracks current and recent workspace directories.

A workspace is a directory path that serves as the root for file operations.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


RECENT_WORKSPACES_FILE = Path("/data/recent_workspaces.json")
MAX_RECENT = 10


@dataclass
class WorkspaceInfo:
    path: str
    name: str = ""
    opened_at: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name or self.path
        if not self.opened_at:
            self.opened_at = datetime.now(timezone.utc).isoformat()


class WorkspaceManager:
    """Manages the current workspace and recent workspace history."""

    def __init__(self):
        self._current: WorkspaceInfo | None = None
        self._recent: list[WorkspaceInfo] = []
        self._load_recent()

    @property
    def current(self) -> WorkspaceInfo | None:
        return self._current

    @property
    def current_path(self) -> str | None:
        return self._current.path if self._current else None

    @property
    def recent(self) -> list[WorkspaceInfo]:
        return list(self._recent)

    def open(self, path: str) -> WorkspaceInfo:
        """Open a workspace at the given path. Returns the workspace info."""
        resolved = str(Path(path).resolve())
        info = WorkspaceInfo(path=resolved)
        self._current = info

        # Move to front of recent list (remove duplicate if exists)
        self._recent = [w for w in self._recent if w.path != resolved]
        self._recent.insert(0, info)
        if len(self._recent) > MAX_RECENT:
            self._recent = self._recent[:MAX_RECENT]

        self._save_recent()
        return info

    def close(self):
        """Close the current workspace."""
        self._current = None

    def switch_to(self, path: str) -> WorkspaceInfo | None:
        """Switch to another workspace at the given path."""
        if self._current and self._current.path == path:
            return self._current
        return self.open(path)

    def validate(self, path: str) -> dict:
        """Validate whether a path is a valid workspace directory."""
        p = Path(path)
        if not p.exists():
            return {"valid": False, "error": "Path does not exist"}
        if not p.is_dir():
            return {"valid": False, "error": "Path is not a directory"}
        return {"valid": True, "path": str(p.resolve())}

    def _load_recent(self):
        """Load recent workspaces from persistent storage."""
        try:
            if RECENT_WORKSPACES_FILE.exists():
                data = json.loads(RECENT_WORKSPACES_FILE.read_text())
                self._recent = [WorkspaceInfo(**item) for item in data]
        except (json.JSONDecodeError, OSError):
            self._recent = []

    def _save_recent(self):
        """Persist recent workspaces list."""
        try:
            RECENT_WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [
                {"path": w.path, "name": w.name, "opened_at": w.opened_at}
                for w in self._recent
            ]
            RECENT_WORKSPACES_FILE.write_text(json.dumps(data, indent=2))
        except OSError:
            pass  # best-effort persistence
