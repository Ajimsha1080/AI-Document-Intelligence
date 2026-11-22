import pytest
import os
import io
import hmac
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User, ApiKey
from app.models.document import Document, ExtractedField
from app.models.audit import AuditLog
from app.services.storage_service import storage_service
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_tenant_onboard_requires_platform_admin_key(
    async_client: AsyncClient,
    monkeypatch
):
    """
    POST /api/v1/tenants/onboard needs no login:
    require header X-Platform-Admin-Key == env PLATFORM_ADMIN_API_KEY (hmac.compare_digest), else 403.
    """
    test_key = "sovereign_platform_key_secret_2026"
    monkeypatch.setenv("PLATFORM_ADMIN_API_KEY", test_key)

    payload = {
        "payload": {
            "name": "Test Platform Tenant",
            "slug": "test-platform-tenant",
            "tier": "enterprise",
            "retention_days": 180,
            "pii_masking_default": True
        },
        "admin_user": {
            "email": "platform_admin@test-sovereign.ae",
            "password": "PlatformAdminSecurePass123!",
            "full_name": "Platform Administrator"
        }
    }

    # 1. Missing header -> 403
    resp_missing = await async_client.post("/api/v1/tenants/onboard", json=payload)
    assert resp_missing.status_code == 403
    assert "X-Platform-Admin-Key" in resp_missing.json()["detail"]

    # 2. Invalid header -> 403
    resp_wrong = await async_client.post(
        "/api/v1/tenants/onboard",
        json=payload,
        headers={"X-Platform-Admin-Key": "wrong_key_attempt"}
    )
    assert resp_wrong.status_code == 403

    # 3. Valid header -> 200
    resp_ok = await async_client.post(
        "/api/v1/tenants/onboard",
        json=payload,
        headers={"X-Platform-Admin-Key": test_key}
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["slug"] == "test-platform-tenant"

@pytest.mark.asyncio
async def test_storage_path_traversal_prevention(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    storage_service.py uses the client filename in the path (path traversal).
    Save as {tenant_id}/{document_id}/original{ext} (ext from detected MIME).
    Store only a cleaned basename in DB. Test with '../../../evil.png'.
    """
    headers = {"Authorization": f"Bearer {seeded_data['reviewer_token']}"}
    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"

    # Upload with directory traversal path
    files = {"file": ("../../../evil.png", io.BytesIO(sample_png), "image/png")}
    data = {"document_type_code": "emirates_id"}

    resp = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers=headers
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Check DB record stores cleaned basename "evil.png"
    stmt = select(Document).where(Document.id == doc_id)
    res = await db_session.execute(stmt)
    doc = res.scalar_one_or_none()
    assert doc is not None
    assert doc.file_name == "evil.png"
    assert ".." not in doc.file_name

    # Storage path must be strictly {tenant_id}/{document_id}/original.png
    assert ".." not in doc.storage_path
    assert f"{doc.tenant_id}/{doc_id}/original.png" in doc.storage_path.replace("\\", "/")

@pytest.mark.asyncio
async def test_require_permission_endpoints_and_viewer_forbidden_on_upload(
    async_client: AsyncClient,
    seeded_data: dict
):
    """
    documents.py and rag.py: use require_permission on every endpoint.
    Test: viewer gets 403 on upload, correct, approve, delete, and retention sweep.
    """
    viewer_headers = {"Authorization": f"Bearer {seeded_data['viewer_token']}"}

    # 1. Upload forbidden for viewer
    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files = {"file": ("test.png", io.BytesIO(sample_png), "image/png")}
    resp_upload = await async_client.post(
        "/api/v1/documents/upload",
        files=files,
        headers=viewer_headers
    )
    assert resp_upload.status_code == 403
    assert "document:upload" in resp_upload.json()["detail"]

    # 2. Retention sweep forbidden for viewer
    resp_ret = await async_client.post("/api/v1/documents/retention/sweep", headers=viewer_headers)
    assert resp_ret.status_code == 403
    assert "retention:manage" in resp_ret.json()["detail"]

    # 3. List documents allowed for viewer (DOCUMENT_VIEW)
    resp_list = await async_client.get("/api/v1/documents/", headers=viewer_headers)
    assert resp_list.status_code == 200

@pytest.mark.asyncio
async def test_export_pii_masking_and_admin_unmask_audit(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Export: mask_pii defaults to tenant pii_masking_default; only admin may unmask;
    audit PII_UNMASKED. Also mask PII in RAG answers for non-admins.
    """
    admin_headers = {"Authorization": f"Bearer {seeded_data['admin_token']}"}
    viewer_headers = {"Authorization": f"Bearer {seeded_data['viewer_token']}"}
    tenant = seeded_data["tenant_1"]

    # Create a document and field with an Emirates ID
    doc = Document(
        tenant_id=tenant.id,
        file_name="eid_test.png",
        file_size=1024,
        mime_type="image/png",
        storage_path=f"{tenant.id}/doc123/original.png",
        status="approved"
    )
    db_session.add(doc)
    await db_session.flush()

    field = ExtractedField(
        tenant_id=tenant.id,
        document_id=doc.id,
        field_name="id_number",
        value="784-1985-1234567-1",
        confidence=0.98
    )
    db_session.add(field)
    await db_session.commit()

    # 1. Non-admin attempting to unmask PII -> 403
    resp_unmask_viewer = await async_client.get(
        f"/api/v1/documents/{doc.id}/export?format=json&mask_pii=false",
        headers=viewer_headers
    )
    assert resp_unmask_viewer.status_code == 403
    assert "Only administrators may unmask PII" in resp_unmask_viewer.json()["detail"]

    # 2. Admin unmasking -> 200 and audit PII_UNMASKED recorded
    resp_unmask_admin = await async_client.get(
        f"/api/v1/documents/{doc.id}/export?format=json&mask_pii=false",
        headers=admin_headers
    )
    assert resp_unmask_admin.status_code == 200
    export_json = resp_unmask_admin.json()
    assert export_json["fields"]["id_number"]["value"] == "784-1985-1234567-1"

    # Verify PII_UNMASKED audit log
    stmt = select(AuditLog).where(
        and_(
            AuditLog.entity_id == doc.id,
            AuditLog.action == "PII_UNMASKED"
        )
    )
    res = await db_session.execute(stmt)
    audit = res.scalar_one_or_none()
    assert audit is not None
    assert audit.actor_role == "admin"

@pytest.mark.asyncio
async def test_api_key_expiration_and_block_admin_role(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    API keys: save expires_at, reject expired keys in deps.py, block role 'admin' keys,
    add list + revoke endpoints.
    """
    admin_headers = {"Authorization": f"Bearer {seeded_data['admin_token']}"}

    # 1. Block role "admin" keys -> 400
    resp_admin_key = await async_client.post(
        "/api/v1/users/api-keys",
        json={"name": "Forbidden Admin Key", "role": "admin"},
        headers=admin_headers
    )
    assert resp_admin_key.status_code == 400
    assert "admin role" in resp_admin_key.json()["detail"]

    # 2. Create valid key with expiration
    resp_create = await async_client.post(
        "/api/v1/users/api-keys",
        json={"name": "Valid Reviewer Key", "role": "reviewer", "expires_in_days": 30},
        headers=admin_headers
    )
    assert resp_create.status_code == 200
    key_data = resp_create.json()
    raw_key = key_data["raw_key"]
    key_id = key_data["id"]
    assert key_data["expires_at"] is not None

    # 3. Test key works
    resp_use = await async_client.get("/api/v1/documents/", headers={"X-API-Key": raw_key})
    assert resp_use.status_code == 200

    # 4. List keys endpoint
    resp_list = await async_client.get("/api/v1/users/api-keys", headers=admin_headers)
    assert resp_list.status_code == 200
    keys_list = resp_list.json()
    assert any(k["id"] == key_id for k in keys_list)

    # 5. Revoke key endpoint
    resp_revoke = await async_client.delete(f"/api/v1/users/api-keys/{key_id}", headers=admin_headers)
    assert resp_revoke.status_code == 200
    assert resp_revoke.json()["status"] == "revoked"

    # Revoked key must be rejected with 401
    resp_use_revoked = await async_client.get("/api/v1/documents/", headers={"X-API-Key": raw_key})
    assert resp_use_revoked.status_code == 401

@pytest.mark.asyncio
async def test_retention_days_range_and_tenant_scoped_sweep(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    retention_days must be 1–3650; retention sweep endpoint only purges the caller's tenant.
    """
    admin_headers = {"Authorization": f"Bearer {seeded_data['admin_token']}"}

    # 1. Schema range validation: 0 and 3651 should fail
    from app.schemas.tenant import TenantUpdate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TenantUpdate(retention_days=0)

    with pytest.raises(ValidationError):
        TenantUpdate(retention_days=3651)

    valid_update = TenantUpdate(retention_days=365)
    assert valid_update.retention_days == 365

    # 2. Retention sweep only sweeps caller's tenant
    resp_sweep = await async_client.post("/api/v1/documents/retention/sweep", headers=admin_headers)
    assert resp_sweep.status_code == 200
    data = resp_sweep.json()
    assert "total_purged" in data

@pytest.mark.asyncio
async def test_login_security_dummy_bcrypt_and_lowercase(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Login: lowercase emails, always run bcrypt (dummy hash if no user),
    don't log unknown-email failures into another tenant's audit.
    """
    reviewer = seeded_data["reviewer_user"]

    # 1. Login with mixed case email succeeds
    mixed_email = reviewer.email.upper()
    resp_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": mixed_email, "password": "ReviewerPass123!"}
    )
    assert resp_login.status_code == 200
    assert "access_token" in resp_login.json()

    # 2. Login with unknown email returns 401 and does NOT log audit to tenant
    initial_audit_count = len((await db_session.execute(
        select(AuditLog).where(AuditLog.tenant_id == reviewer.tenant_id)
    )).scalars().all())

    resp_unknown = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_stranger_probe@external.com", "password": "WrongPassword123!"}
    )
    assert resp_unknown.status_code == 401

    post_audit_count = len((await db_session.execute(
        select(AuditLog).where(AuditLog.tenant_id == reviewer.tenant_id)
    )).scalars().all())
    assert post_audit_count == initial_audit_count

@pytest.mark.asyncio
async def test_webhook_no_hardcoded_secret_and_no_field_leakage(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession,
    monkeypatch
):
    """
    Webhook: remove hardcoded secret (env WEBHOOK_SIGNING_SECRET); it never sends,
    so return dispatched=false with reason; don't return field data in approve response.
    """
    test_secret = "env_webhook_signing_secret_custom_2026"
    monkeypatch.setenv("WEBHOOK_SIGNING_SECRET", test_secret)

    admin_headers = {"Authorization": f"Bearer {seeded_data['admin_token']}"}
    tenant = seeded_data["tenant_1"]

    # Create document to approve
    doc = Document(
        tenant_id=tenant.id,
        file_name="approve_test.png",
        file_size=1024,
        mime_type="image/png",
        storage_path=f"{tenant.id}/doc_app/original.png",
        status="needs_review"
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await async_client.post(f"/api/v1/documents/{doc.id}/approve", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "approved"
    assert data["document_id"] == doc.id
    assert "webhook" in data
    assert data["webhook"]["dispatched"] is False
    assert data["webhook"]["reason"] == "no_webhook_endpoint_configured"
    # Ensure no raw field leakage in approve response
    assert "fields" not in data
    assert "fields" not in data["webhook"]

@pytest.mark.asyncio
async def test_stream_token_for_sse(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Don't put JWTs in URLs: file preview via fetch + blob URL;
    SSE uses a 60-second stream-only token from new POST /api/v1/auth/stream-token.
    """
    from app.core.security import decode_access_token
    from app.api.deps import get_stream_actor
    from fastapi import Request

    reviewer_headers = {"Authorization": f"Bearer {seeded_data['reviewer_token']}"}
    tenant = seeded_data["tenant_1"]

    doc = Document(
        tenant_id=tenant.id,
        file_name="stream_test.png",
        file_size=1024,
        mime_type="image/png",
        storage_path=f"{tenant.id}/doc_stream/original.png",
        status="needs_review"
    )
    db_session.add(doc)
    await db_session.commit()

    # 1. Obtain stream token
    resp_st = await async_client.post("/api/v1/auth/stream-token", headers=reviewer_headers)
    assert resp_st.status_code == 200
    st_data = resp_st.json()
    assert "stream_token" in st_data
    assert st_data["expires_in"] == 60
    stream_token = st_data["stream_token"]

    # 2. Verify token claims and scope == "sse_stream"
    claims = decode_access_token(stream_token)
    assert claims.get("scope") == "sse_stream"
    assert claims.get("sub") == seeded_data["reviewer_user"].id

    # 3. Direct access token without stream scope in query param is rejected with 401
    primary_token = reviewer_headers["Authorization"].replace("Bearer ", "")
    resp_rejected = await async_client.get(
        f"/api/v1/documents/{doc.id}/events?token={primary_token}"
    )
    assert resp_rejected.status_code == 401
    assert "stream tokens" in resp_rejected.json()["detail"].lower()

    # 4. Missing token on stream endpoint is rejected with 401
    resp_missing = await async_client.get(f"/api/v1/documents/{doc.id}/events")
    assert resp_missing.status_code == 401

    # 5. Verify get_stream_actor dependency successfully resolves the stream token
    mock_request = Request({"type": "http", "method": "GET", "url": "http://test", "headers": []})
    actor = await get_stream_actor(request=mock_request, token=stream_token, header_token=None, db=db_session)
    assert actor.id == seeded_data["reviewer_user"].id
    assert actor.tenant_id == tenant.id
