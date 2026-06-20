"""ComputeClient: Python HTTP client for Rust compute node.

Provides fallback-safe access to CodeGraph and SmartCrusher endpoints.
All methods gracefully degrade when the Rust node is unavailable.
"""

import json
from typing import Any

import httpx


class ComputeClient:
    """HTTP client for the Rust compute microservice."""

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def health(self) -> bool:
        """Check if the compute node is healthy."""
        try:
            resp = await self._client.get(f"{self.base_url}/health", timeout=3.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def index_project(self, path: str) -> dict[str, Any]:
        """Index a project directory. Returns node/edge counts."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/graph/index",
                json={"path": path},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"nodes": 0, "edges": 0}

    async def explore(self, symbol: str, depth: int = 5) -> dict[str, Any]:
        """Explore a symbol's context in the codegraph."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/graph/explore",
                json={"symbol": symbol, "depth": depth},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"context": "", "related": []}

    async def find_callers(self, node_id: str, depth: int = 2) -> list[dict]:
        """Find callers of a given function/node."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/graph/callers",
                json={"node_id": node_id, "depth": depth},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    async def impact(self, node_id: str, alpha: float = 0.25) -> list[dict]:
        """Compute impact radius via RWR PageRank."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/graph/impact",
                json={"node_id": node_id, "alpha": alpha},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []

    async def crush_json(self, content: str, query: str | None = None) -> dict[str, Any] | None:
        """Compress JSON content using SmartCrusher."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/compress/crush",
                json={"content": content, "query": query},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
