from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users):
    """Test successful login with correct credentials."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient, test_users):
    """Test login failure with invalid password."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_users):
    """Test getting current user details using access token."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "employee@test.com"
    assert user_data["role"] == "employee"


@pytest.mark.asyncio
async def test_role_based_access_denied(client: AsyncClient, test_users):
    """Test that normal employee cannot access admin-only endpoints."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]

    # Endpoint `/api/users` is restricted to admin role
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
