import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_test_webhook_endpoint(async_client: AsyncClient, seeded_data: dict, db_session):
    admin_token = seeded_data["admin_token"]
    viewer_token = seeded_data["viewer_token"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Test without webhook URL configured
    resp = await async_client.post("/api/v1/tenants/test-webhook", json={}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["dispatched"] is False
    assert data["reason"] == "no_webhook_endpoint_configured"

    # Viewer role forbidden (403)
    resp_viewer = await async_client.post("/api/v1/tenants/test-webhook", json={"url": "https://example.com/webhook"}, headers=viewer_headers)
    assert resp_viewer.status_code == 403

    # Admin role permitted with webhook url and secret passed
    resp_admin = await async_client.post(
        "/api/v1/tenants/test-webhook",
        json={"url": "https://example.com/webhook", "secret": "test_signing_secret_12345"},
        headers=admin_headers
    )
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert data_admin["dispatched"] is False
    assert data_admin["target_url"] == "https://example.com/webhook"
    assert data_admin["reason"] == "webhook_dispatch_offline"
    assert data_admin["signature"] is not None
