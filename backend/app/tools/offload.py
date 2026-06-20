"""Offload manager: persist large tool results to disk.

Threshold configurable via config.agent_offload_threshold_bytes.
"""

import hashlib
import json
from pathlib import Path

from app.config import config


class OffloadManager:
    """Manage offloading of large results to filesystem storage."""

    def __init__(self, storage_dir: str = "/data/offload", threshold: int | None = None):
        self._storage = Path(storage_dir)
        self._storage.mkdir(parents=True, exist_ok=True)
        self._threshold = threshold or config.agent_offload_threshold_bytes

    async def store(self, content: str) -> str:
        """Store content if larger than threshold. Returns reference string."""
        if len(content) <= self._threshold:
            return content

        key = hashlib.sha256(content.encode()).hexdigest()[:16]
        path = self._storage / f"{key}.json"
        path.write_text(json.dumps({"size": len(content), "content": content}))
        return f"[offloaded: {key}]"

    async def load(self, ref: str) -> str:
        """Load offloaded content by reference."""
        if not ref.startswith("[offloaded:"):
            return ref
        key = ref[len("[offloaded: "):-1]
        path = self._storage / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())["content"]
        return ref
