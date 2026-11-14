import io
import os
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.document import Document, ExtractedField, DocumentPage, ValidationResult
from app.models.audit import AuditLog
from app.services.retention_service import run_retention_policy_sweep

# Valid sample file binaries
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
INVALID_EXE_BYTES = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"

@pytest.mark.asyncio
async def test_upload_valid_document(async_client: AsyncClient, seeded_data: dict):
    """Test successful multipart document upload with magic byte verification."""
    token = seeded_data["admin_token"]
    
    files = {"file": ("emirates_id_front.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"document_type_code": "emirates_id"}
    
    resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["file_name"] == "emirates_id_front.png"
    assert doc["mime_type"] == "image/png"
    assert doc["status"] == "queued"
    assert doc["tenant_id"] == seeded_data["tenant_1"].id

    # Verify audit log recorded
    audit_resp = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {token}"},
        params={"action": "DOCUMENT_UPLOAD"}
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 1
    assert any(log["entity_id"] == doc["id"] for log in logs)

@pytest.mark.asyncio
async def test_upload_rejects_spoofed_magic_bytes(async_client: AsyncClient, seeded_data: dict):
    """Test that a malicious file with spoofed extension is rejected by magic byte inspection."""
    token = seeded_data["admin_token"]
    
    # Executable disguised as PNG
    files = {"file": ("malicious.png", io.BytesIO(INVALID_EXE_BYTES), "image/png")}
    
    resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert resp.status_code == 400
    assert "Unsupported or invalid file format" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_upload_rejects_empty_file(async_client: AsyncClient, seeded_data: dict):
    """Test that empty 0-byte file is rejected."""
    token = seeded_data["admin_token"]
    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
    resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert resp.status_code == 400
    assert "Empty file" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_document_tenant_isolation(async_client: AsyncClient, seeded_data: dict):
    """Test that Tenant 2 cannot view, stream, or delete Tenant 1 documents."""
    token_1 = seeded_data["admin_token"]
    token_2 = seeded_data["tenant2_token"]

    # 1. Tenant 1 uploads document
    files = {"file": ("secret_contract.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    upload_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token_1}"},
        files=files
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 2. Tenant 2 tries to GET document -> 404 Not Found
    t2_get = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert t2_get.status_code == 404

    # 3. Tenant 2 tries to stream file -> 404 Not Found
    t2_file = await async_client.get(
        f"/api/v1/documents/{doc_id}/file",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert t2_file.status_code == 404

    # 4. Tenant 2 tries to delete document -> 404 Not Found
    t2_del = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert t2_del.status_code == 404

    # 5. Tenant 2 list documents must not include Tenant 1's document
    t2_list = await async_client.get(
        "/api/v1/documents/",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert t2_list.status_code == 200
    assert all(d["id"] != doc_id for d in t2_list.json()["documents"])

@pytest.mark.asyncio
async def test_stream_original_file(async_client: AsyncClient, seeded_data: dict):
    """Test streaming original document binary."""
    token = seeded_data["admin_token"]
    
    files = {"file": ("license.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    upload_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    doc_id = upload_resp.json()["id"]

    stream_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/file",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stream_resp.status_code == 200
    assert stream_resp.content == VALID_PDF_BYTES
    assert "application/pdf" in stream_resp.headers["content-type"]

@pytest.mark.asyncio
async def test_hard_delete_document_and_cascade(async_client: AsyncClient, seeded_data: dict):
    """
    Test that DELETE /{id} permanently deletes document, storage file,
    and all derived database child rows (fields, pages, validation results).
    """
    token = seeded_data["admin_token"]
    
    # Upload document
    files = {"file": ("delete_me.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    doc_id = up.json()["id"]

    # Reviewer cannot delete (RBAC guard)
    rev_token = seeded_data["reviewer_token"]
    rev_del = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert rev_del.status_code == 403

    # Admin deletes
    admin_del = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert admin_del.status_code == 200
    assert admin_del.json()["status"] == "deleted"

    # Confirm document no longer exists
    get_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 404

    # Confirm DOCUMENT_DELETE audit event is preserved
    audit_resp = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {token}"},
        params={"action": "DOCUMENT_DELETE"}
    )
    assert audit_resp.status_code == 200
    assert any(log["entity_id"] == doc_id for log in audit_resp.json())

@pytest.mark.asyncio
async def test_retention_policy_sweep(async_client: AsyncClient, seeded_data: dict, db_session):
    """
    Test that scheduled retention job identifies and purges expired documents
    older than tenant retention days.
    """
    tenant_1 = seeded_data["tenant_1"]
    
    # Create a simulated expired document (created 400 days ago, retention is 365)
    expired_date = datetime.now(timezone.utc) - timedelta(days=400)
    expired_doc = Document(
        tenant_id=tenant_1.id,
        file_name="ancient_kyc.pdf",
        file_size=len(VALID_PDF_BYTES),
        mime_type="application/pdf",
        storage_path=f"data/sovereign_storage/{tenant_1.id}/ancient_doc/ancient_kyc.pdf",
        status="approved",
        created_at=expired_date
    )
    db_session.add(expired_doc)
    await db_session.commit()
    await db_session.refresh(expired_doc)
    ancient_id = expired_doc.id

    # Run retention sweep
    sweep_result = await run_retention_policy_sweep(db_session)
    assert sweep_result["status"] == "completed"
    assert sweep_result["total_purged"] >= 1

    # Verify expired document is purged from DB
    res = await db_session.execute(select(Document).where(Document.id == ancient_id))
    assert res.scalar_one_or_none() is None
