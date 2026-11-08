import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_authentication_login_flow(async_client: AsyncClient, seeded_data: dict):
    # Valid login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@adcb.ae", "password": "AdminPass123!"}
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["tenant_id"] == seeded_data["tenant_1"].id

    # Invalid login
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@adcb.ae", "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401

@pytest.mark.asyncio
async def test_rbac_reviewer_cannot_manage_users(async_client: AsyncClient, seeded_data: dict):
    # Reviewer attempts to create a user -> 403 Forbidden
    resp = await async_client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {seeded_data['reviewer_token']}"},
        json={
            "email": "hacker@demo.ae",
            "password": "Password123!",
            "full_name": "Unauthorized Attempt",
            "role": "admin"
        }
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_rbac_viewer_cannot_seed_schemas(async_client: AsyncClient, seeded_data: dict):
    # Viewer attempts to modify document schemas -> 403 Forbidden
    resp = await async_client.post(
        "/api/v1/document-types/seed-defaults",
        headers={"Authorization": f"Bearer {seeded_data['viewer_token']}"}
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_api_key_generation_and_authentication(async_client: AsyncClient, seeded_data: dict):
    # Admin creates an API key
    key_resp = await async_client.post(
        "/api/v1/users/api-keys",
        headers={"Authorization": f"Bearer {seeded_data['admin_token']}"},
        json={"name": "Core Banking ERP Connector", "role": "api_client"}
    )
    assert key_resp.status_code == 200
    raw_key = key_resp.json()["raw_key"]
    assert raw_key.startswith("uae_live_")

    # Use API key to query /auth/me
    auth_me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": raw_key}
    )
    assert auth_me_resp.status_code == 200
    assert auth_me_resp.json()["is_api_client"] is True
    assert auth_me_resp.json()["tenant"]["id"] == seeded_data["tenant_1"].id
