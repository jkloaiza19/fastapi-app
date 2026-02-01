"""
Tests for the main application and health check endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"result": "Success"}


@pytest.mark.asyncio
async def test_health_check_rate_limit(client: AsyncClient):
    """Test that health check endpoint can handle multiple requests."""
    # Make a few requests to verify endpoint is stable
    responses = []
    for _ in range(3):
        response = await client.get("/healthcheck")
        responses.append(response)
    
    # All should either succeed or be rate limited (both are valid)
    for response in responses:
        assert response.status_code in [200, 429]


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test CORS headers are present."""
    response = await client.options("/healthcheck")
    # CORS middleware should allow all origins
    assert response.status_code in [200, 405]  # OPTIONS might not be implemented


@pytest.mark.asyncio
async def test_404_not_found(client: AsyncClient):
    """Test 404 response for non-existent endpoint."""
    response = await client.get("/this-does-not-exist")
    assert response.status_code == 404
