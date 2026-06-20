"""Tests for ComputeClient (Rust compute node HTTP client)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.compute_client import ComputeClient


def _mock_response(json_data: dict, status: int = 200):
    """Create a mock httpx Response with async json()."""
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = json_data
    if status >= 400:
        mock.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        mock.raise_for_status.return_value = None
    return mock


@pytest.mark.asyncio
async def test_health_returns_true_when_ok():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response({"status": "ok"})
        result = await client.health()
        assert result is True


@pytest.mark.asyncio
async def test_health_returns_false_on_error():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        from httpx import ConnectError
        mock_get.side_effect = ConnectError("connection failed")
        result = await client.health()
        assert result is False


@pytest.mark.asyncio
async def test_index_project():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response({"nodes": 10, "edges": 20})
        result = await client.index_project("/test/path")
        assert result["nodes"] == 10
        assert result["edges"] == 20


@pytest.mark.asyncio
async def test_index_project_fallback_on_error():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("timeout")
        result = await client.index_project("/test/path")
        assert result == {"nodes": 0, "edges": 0}


@pytest.mark.asyncio
async def test_crush_json():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(
            {"compressed": "[1,2,3]", "saved_ratio": 0.7}
        )
        result = await client.crush_json("[1,2,3,4,5,6,7,8,9,10]")
        assert result is not None
        assert result["saved_ratio"] == 0.7


@pytest.mark.asyncio
async def test_crush_json_fallback_on_error():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("timeout")
        result = await client.crush_json("[1,2,3]")
        assert result is None


@pytest.mark.asyncio
async def test_explore():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_response(
            {"context": "symbol info", "related": ["caller: main"]}
        )
        result = await client.explore("hello", depth=3)
        assert result["context"] == "symbol info"


@pytest.mark.asyncio
async def test_close():
    client = ComputeClient(base_url="http://test:8080")
    with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()
