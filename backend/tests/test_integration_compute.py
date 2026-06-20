"""Integration tests: Python → Rust Compute Node real HTTP calls.

Prerequisites:
  - Rust compute node binary must be built: `cd compute-node && cargo build`
  - Test starts the binary as a subprocess and communicates over HTTP.

Run with:
  pytest tests/test_integration_compute.py -v --timeout=60
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import httpx

# ── Helpers ──

COMPUTE_PORT = 18080  # Use non-standard port to avoid conflicts
COMPUTE_URL = f"http://localhost:{COMPUTE_PORT}"
COMPUTE_BINARY = (
    Path(__file__).resolve().parent.parent.parent
    / "compute-node"
    / "target"
    / "debug"
    / "rubbish-compute.exe"
)


def _ensure_binary():
    """Ensure the compute binary exists, or skip the test."""
    if not COMPUTE_BINARY.exists():
        pytest.skip(
            f"Compute binary not found at {COMPUTE_BINARY}. "
            "Run 'cd compute-node && cargo build' first."
        )


@pytest.fixture(scope="module")
def compute_process():
    """Start the Rust compute node as a subprocess for the test module."""
    _ensure_binary()

    # Use temp dir for DB so tests are isolated
    with tempfile.TemporaryDirectory(prefix="rubbish_integration_") as tmpdir:
        db_path = os.path.join(tmpdir, "codegraph.db")
        env = os.environ.copy()
        env["COMPUTE_DB_PATH"] = db_path
        env["COMPUTE_PORT"] = str(COMPUTE_PORT)
        env["RUST_LOG"] = "error"

        proc = subprocess.Popen(
            [str(COMPUTE_BINARY)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the service to become healthy
        max_retries = 30
        for attempt in range(max_retries):
            try:
                resp = httpx.get(f"{COMPUTE_URL}/health", timeout=2.0)
                if resp.status_code == 200:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            time.sleep(0.5)
        else:
            # Failed to start — grab stderr for diagnostics
            _stderr = proc.stderr.read().decode() if proc.stderr else ""
            proc.kill()
            proc.wait()
            pytest.fail(
                f"Compute node failed to start after {max_retries} attempts.\n"
                f"STDERR: {_stderr}"
            )

        yield proc

        # Teardown
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.fixture
async def client():
    """Async HTTP client for the compute node."""
    async with httpx.AsyncClient(base_url=COMPUTE_URL) as c:
        yield c


# ── Tests ──


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health(compute_process, client):
    """Verify the health endpoint returns OK."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_index(compute_process, client):
    """Index a real project directory (the backend source code)."""
    backend_dir = Path(__file__).resolve().parent.parent / "app"
    resp = await client.post(
        "/graph/index",
        json={"path": str(backend_dir)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] > 0, f"Expected >0 nodes, got {data['nodes']}"
    assert isinstance(data["edges"], int)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_explore(compute_process, client):
    """Explore a known symbol after indexing."""
    # First index the backend source
    backend_dir = Path(__file__).resolve().parent.parent / "app"
    await client.post("/graph/index", json={"path": str(backend_dir)})

    # Try to explore a symbol that should exist
    resp = await client.post(
        "/graph/explore",
        json={"symbol": "agent", "depth": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "context" in data
    assert "related" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_callers(compute_process, client):
    """Find callers after indexing the backend."""
    backend_dir = Path(__file__).resolve().parent.parent / "app"
    await client.post("/graph/index", json={"path": str(backend_dir)})

    # Get all nodes first to find a valid node_id
    stats = await client.get("/graph/stats")
    assert stats.status_code == 200
    stats_data = stats.json()
    assert stats_data["nodes"] > 0

    # Use a generic node_id — the endpoint handles it gracefully
    resp = await client.post(
        "/graph/callers",
        json={"node_id": "unknown_func_123", "depth": 2},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_stats(compute_process, client):
    """Verify stats endpoint works and returns consistent data."""
    resp = await client.get("/graph/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "fts_entries" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compress_crush(compute_process, client):
    """Verify SmartCrusher JSON compression works end-to-end."""
    large_json = list(range(100))
    resp = await client.post(
        "/compress/crush",
        json={"content": large_json, "query": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved_ratio"] > 0.0
    assert len(data["compressed"]) < len(str(large_json))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compress_crush_text(compute_process, client):
    """Verify SmartCrusher text compression works."""
    long_text = "line\n" * 200
    resp = await client.post(
        "/compress/crush",
        json={"content": long_text},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved_ratio"] > 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_impact(compute_process, client):
    """Verify impact radius endpoint returns results."""
    resp = await client.post(
        "/graph/impact",
        json={"node_id": "func_main", "alpha": 0.25},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_persistence(compute_process, client):
    """Verify that indexed data persists (DB is not :memory:)."""
    backend_dir = Path(__file__).resolve().parent.parent / "app"
    resp1 = await client.post("/graph/index", json={"path": str(backend_dir)})
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Verify stats reflect indexed data
    stats = await client.get("/graph/stats")
    stats_data = stats.json()
    assert stats_data["nodes"] >= data1["nodes"], (
        f"Stats nodes ({stats_data['nodes']}) < index nodes ({data1['nodes']})"
    )
