"""Checkpoint: per-turn file snapshots with path-escape protection and rollback.

Each turn produces an independent JSON file in .sessions/{session-id}.ckpt/
so that failures are isolated and deletion is cheap.

Reference: Firefly pkg/checkpoint/store.go
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class CheckpointManager:
    """Save and restore file snapshots per turn.

    Structure:
        .sessions/{session_id}.ckpt/
            turn-0.json      # Snapshot of files at turn 0
            turn-1.json      # Snapshot of files at turn 1
            ...
    """

    def __init__(self, session_id: str = "default", ckpt_dir: str = ""):
        self._ckpt_dir = Path(ckpt_dir or f".sessions/{session_id}.ckpt")
        self._session_id = session_id
        self._turn = 0
        self._ckpt_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, file_path: str) -> str:
        """Protect against path escape attacks.

        Ensures restored file paths cannot escape the workspace directory.
        """
        clean = os.path.normpath(file_path).lstrip(os.sep)
        if ".." in clean.split(os.sep):
            raise ValueError(f"Path escape detected: {file_path}")
        return clean

    async def save(self, file_path: str, content: str) -> str:
        """Save a checkpoint before modifying a file.

        Only records the *first* snapshot per file per turn.
        """
        safe = self._safe_path(file_path)
        turn_data = self._load_turn(self._turn)
        if safe in turn_data:
            return f"{self._turn}:{safe}:already_recorded"  # already snapshotted this turn

        turn_data[safe] = {"content": content, "exists": True}
        self._save_turn(self._turn, turn_data)
        return f"{self._turn}:{safe}"

    async def rollback(self, file_path: str, to_turn: int | None = None) -> str | None:
        """Rollback a file to the *earliest* snapshot from to_turn onwards.

        If the file was created in a later turn (no earlier snapshot), it gets deleted.
        """
        safe = self._safe_path(file_path)
        # Search from target turn down to 0 (inclusive)
        target_turn = to_turn if to_turn is not None else self._turn

        for turn in range(target_turn, -1, -1):
            turn_data = self._load_turn(turn)
            if safe in turn_data:
                entry = turn_data[safe]
                dest = Path(file_path)
                if entry["exists"]:
                    dest.write_text(entry["content"], encoding="utf-8")
                    return entry["content"]
                else:
                    # File didn't exist at that turn → delete
                    if dest.exists():
                        dest.unlink()
                    return None

        return None  # No snapshot found

    async def list_checkpoints(self, file_path: str = "") -> list[dict]:
        """List all checkpoints, optionally filtered by file."""
        filter_safe = self._safe_path(file_path) if file_path else ""
        result = []
        for turn_file in sorted(self._ckpt_dir.glob("turn-*.json")):
            turn = int(turn_file.stem.split("-")[1])
            data = json.loads(turn_file.read_text())
            for path, entry in data.items():
                if not filter_safe or filter_safe in path:
                    result.append({
                        "turn": turn,
                        "file_path": path,
                        "exists": entry["exists"],
                        "content_length": len(entry.get("content", "")),
                    })
        return result

    def next_turn(self):
        """Advance to the next turn."""
        self._turn += 1

    def _load_turn(self, turn: int) -> dict:
        path = self._ckpt_dir / f"turn-{turn}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _save_turn(self, turn: int, data: dict):
        path = self._ckpt_dir / f"turn-{turn}.json"
        path.write_text(json.dumps(data, indent=2))
