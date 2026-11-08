import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_tenant_user_isolation(async_client: AsyncClient, seeded_data: dict):
    # Query users as Tenant 1 Admin
    resp1 = await async_client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {seeded_data['admin_token']}"}
    )
    assert resp1.status_code == 200
    users_t1 = resp1.json()
    assert len(users_t1) == 3
    emails_t1 = [u["email"] for u in users_t1]
    assert "admin@adcb.ae" in emails_t1
    assert "admin@enbd.ae" not in emails_t1 # Tenant 2 user MUST NOT be visible

    # Query users as Tenant 2 Admin
    resp2 = await async_client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {seeded_data['tenant2_token']}"}
    )
    assert resp2.status_code == 200
    users_t2 = resp2.json()
    assert len(users_t2) == 1
    assert users_t2[0]["email"] == "admin@enbd.ae"

@pytest.mark.asyncio
async def test_document_types_tenant_isolation(async_client: AsyncClient, seeded_data: dict):
    # Seed default document types for Tenant 1
    seed_resp = await async_client.post(
        "/api/v1/document-types/seed-defaults",
        headers={"Authorization": f"Bearer {seeded_data['admin_token']}"}
    )
    assert seed_resp.status_code == 200
    t1_schemas = seed_resp.json()
    assert len(t1_schemas) >= 2

    # Verify Tenant 2 currently has 0 schemas (complete isolation)
    t2_resp = await async_client.get(
        "/api/v1/document-types/",
        headers={"Authorization": f"Bearer {seeded_data['tenant2_token']}"}
    )
    assert t2_resp.status_code == 200
    assert len(t2_resp.json()) == 0

@pytest.mark.asyncio
async def test_tenant_settings_modification_isolation(async_client: AsyncClient, seeded_data: dict):
    # Tenant 1 updates retention days to 90
    update_resp = await async_client.patch(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {seeded_data['admin_token']}"},
        json={"retention_days": 90}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["retention_days"] == 90

    # Tenant 2 verifies their retention policy was unaffected (still 365)
    t2_resp = await async_client.get(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {seeded_data['tenant2_token']}"}
    )
    assert t2_resp.status_code == 200
    assert t2_resp.json()["retention_days"] == 365
