"""
Tests for API key authentication.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_key_required_valid_key(client: AsyncClient, auth_headers: dict, mock_openai_client, mock_astra_db):
    """Test endpoint with valid API key."""
    response = await client.post(
        "/v1/ai/rag/ask",
        headers=auth_headers,
        json={"question": "What is FastAPI?"}
    )
    
    # May return 200 or 404 depending on RAG setup
    # Key is that it doesn't return 401 or 403
    assert response.status_code not in [401, 403]


@pytest.mark.asyncio
async def test_api_key_required_missing_key(client: AsyncClient):
    """Test endpoint without API key."""
    response = await client.post(
        "/v1/ai/rag/ask",
        json={"question": "What is FastAPI?"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "X-API-Key header required"


@pytest.mark.asyncio
async def test_api_key_required_invalid_key(client: AsyncClient):
    """Test endpoint with invalid API key."""
    response = await client.post(
        "/v1/ai/rag/ask",
        headers={"X-API-Key": "invalid-key"},
        json={"question": "What is FastAPI?"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API key"


@pytest.mark.asyncio
async def test_api_key_run_sync(client: AsyncClient, auth_headers: dict, mock_astra_db, monkeypatch):
    """Test run-sync endpoint with valid API key."""
    # Mock the NotionAstraSync to avoid real Astra DB calls
    from unittest.mock import MagicMock
    import asyncio
    
    # Create async run method
    async def mock_run():
        return {"status": "success", "synced": 0}
    
    mock_sync = MagicMock()
    mock_sync.run = mock_run
    
    monkeypatch.setattr("utils.notion_loader.NotionAstraSync", lambda *args: mock_sync)
    
    response = await client.post(
        "/v1/ai/run-sync",
        headers=auth_headers
    )
    
    # Should not return auth errors
    assert response.status_code not in [401, 403]
