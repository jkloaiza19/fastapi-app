"""
Tests for AI endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_completion_missing_data(client: AsyncClient):
    """Test chat completion with missing data."""
    response = await client.post("/v1/ai/chat-completion", json={})
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_chat_completion_invalid_prompt(client: AsyncClient):
    """Test chat completion with invalid prompt."""
    response = await client.post(
        "/v1/ai/chat-completion",
        json={"prompt": ""}  # Empty prompt
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rag_ask_missing_question(client: AsyncClient, auth_headers: dict):
    """Test RAG ask endpoint with missing question."""
    response = await client.post(
        "/v1/ai/rag/ask",
        headers=auth_headers,
        json={}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rag_ask_empty_question(client: AsyncClient, auth_headers: dict):
    """Test RAG ask endpoint with empty question."""
    response = await client.post(
        "/v1/ai/rag/ask",
        headers=auth_headers,
        json={"question": ""}
    )
    
    assert response.status_code == 422
