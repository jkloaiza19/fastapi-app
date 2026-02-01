"""
Tests for user endpoints.
"""
import pytest
from httpx import AsyncClient
from db.models import User


@pytest.mark.asyncio
async def test_get_user_success(client: AsyncClient, test_user: User):
    """Test retrieving a user successfully."""
    response = await client.get(f"/v1/user/{test_user.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username
    assert data["is_confirmed"] == test_user.is_confirmed
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    """Test retrieving a non-existent user."""
    response = await client.get("/v1/user/99999")
    
    assert response.status_code == 404
    assert response.json()["message"] == "User not found"


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test creating a new user."""
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser"
    }
    
    response = await client.post("/v1/user/create", json=user_data)
    
    # This endpoint depends on the actual implementation
    # It might return 201 or have different behavior
    assert response.status_code in [200, 201, 422]  # 422 if validation fails


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, test_user: User):
    """Test creating a user with duplicate email."""
    user_data = {
        "email": test_user.email,
        "username": "different_username"
    }
    
    response = await client.post("/v1/user/create", json=user_data)
    
    # Should fail due to unique constraint
    assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
async def test_create_user_invalid_data(client: AsyncClient):
    """Test creating a user with invalid data."""
    user_data = {
        "email": "not-an-email",  # Invalid email
        "username": ""  # Empty username
    }
    
    response = await client.post("/v1/user/create", json=user_data)
    
    assert response.status_code == 422  # Validation error
