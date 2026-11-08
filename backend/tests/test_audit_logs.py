import pytest
from httpx import AsyncClient
from app.core.security import mask_pii_value

@pytest.mark.asyncio
async def test_pii_masking_utility():
    # Emirates ID masking
    eid = "784-1988-1234567-1"
    masked_eid = mask_pii_value("id_number", eid)
    assert masked_eid == "784-****-*******-1"

    # Email masking
    email = "fatima.alzaabi@adcb.ae"
    masked_email = mask_pii_value("email", email)
    assert masked_email.startswith("f***")
    assert "@adcb.ae" in masked_email

@pytest.mark.asyncio
async def test_audit_logs_recorded_and_isolated(async_client: AsyncClient, seeded_data: dict):
    # Perform an action as Tenant 1 Admin (e.g. login)
    await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@adcb.ae", "password": "AdminPass123!"}
    )

    # Query audit logs as Tenant 1 Admin
    logs_resp1 = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {seeded_data['admin_token']}"}
    )
    assert logs_resp1.status_code == 200
    logs_t1 = logs_resp1.json()
    assert len(logs_t1) > 0
    assert any(log["action"] == "AUTH_LOGIN_SUCCESS" for log in logs_t1)

    # Verify all returned logs strictly belong to Tenant 1
    for log in logs_t1:
        assert log["tenant_id"] == seeded_data["tenant_1"].id

    # Tenant 2 Admin queries audit logs -> should NOT see Tenant 1 logs
    logs_resp2 = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {seeded_data['tenant2_token']}"}
    )
    assert logs_resp2.status_code == 200
    logs_t2 = logs_resp2.json()
    for log in logs_t2:
        assert log["tenant_id"] == seeded_data["tenant_2"].id

@pytest.mark.asyncio
async def test_audit_log_access_control(async_client: AsyncClient, seeded_data: dict):
    # Reviewer attempts to view audit logs -> 403 Forbidden
    resp = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {seeded_data['reviewer_token']}"}
    )
    assert resp.status_code == 403
