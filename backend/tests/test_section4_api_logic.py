import io
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select, and_

from app.models.document import Document, ExtractedField, ValidationResult
from app.models.document_type import DocumentType
from app.models.user import User
from app.core.security import hash_password
from app.core.config import settings
from app.worker.sweeper import sweep_stuck_jobs


@pytest.mark.asyncio
async def test_status_transition_rules_and_conflict_errors(async_client: AsyncClient, seeded_data: dict, db_session):
    """
    Status rules:
    - approve only from needs_review/approved and not with failed error validations (unless admin force=true); else 409
    - reject from needs_review/approved; else 409
    - correct only from needs_review; else 409
    """
    admin_token = seeded_data["admin_token"]
    reviewer_token = seeded_data["reviewer_token"]
    tenant_id = seeded_data["tenant_1"].id

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    # 1. Document in 'uploaded' state (cannot approve, reject, or correct)
    doc_uploaded = Document(
        tenant_id=tenant_id,
        file_name="doc_uploaded.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://doc_uploaded.png",
        status="uploaded"
    )
    db_session.add(doc_uploaded)
    await db_session.commit()
    await db_session.refresh(doc_uploaded)

    # Approve from 'uploaded' -> 409
    res_app = await async_client.post(f"/api/v1/documents/{doc_uploaded.id}/approve", headers=admin_headers)
    assert res_app.status_code == 409

    # Reject from 'uploaded' -> 409
    res_rej = await async_client.post(
        f"/api/v1/documents/{doc_uploaded.id}/reject",
        headers=admin_headers,
        json={"rejection_reason": "Invalid document"}
    )
    assert res_rej.status_code == 409

    # Correct field from 'uploaded' -> 409
    res_corr = await async_client.patch(
        f"/api/v1/documents/{doc_uploaded.id}/fields/id_number",
        headers=reviewer_headers,
        json={"corrected_value": "784-1990-1234567-1", "reason": "fixing typo"}
    )
    assert res_corr.status_code == 409

    # 2. Document in 'needs_review' with failed error validation
    doc_review = Document(
        tenant_id=tenant_id,
        file_name="doc_review.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://doc_review.png",
        status="needs_review",
        confidence_score=0.75
    )
    db_session.add(doc_review)
    await db_session.flush()

    field = ExtractedField(
        tenant_id=tenant_id,
        document_id=doc_review.id,
        field_name="id_number",
        value="784-0000-0000000-0",
        raw_value="784-0000-0000000-0",
        confidence=0.50,
        page_number=1
    )
    val_err = ValidationResult(
        tenant_id=tenant_id,
        document_id=doc_review.id,
        rule_name="EMIRATES_ID_FORMAT_AND_CHECKSUM",
        passed=False,
        severity="error",
        message="Checksum error"
    )
    db_session.add_all([field, val_err])
    await db_session.commit()

    # Normal approve fails with 409 due to failed error validation
    res_norm_app = await async_client.post(f"/api/v1/documents/{doc_review.id}/approve", headers=admin_headers)
    assert res_norm_app.status_code == 409

    # Reviewer cannot force approve -> 409
    res_rev_force = await async_client.post(f"/api/v1/documents/{doc_review.id}/approve?force=true", headers=reviewer_headers)
    assert res_rev_force.status_code == 409

    # Admin with force=true succeeds
    res_admin_force = await async_client.post(f"/api/v1/documents/{doc_review.id}/approve?force=true", headers=admin_headers)
    assert res_admin_force.status_code == 200
    assert res_admin_force.json()["status"] == "approved"
    assert res_admin_force.json()["force_override"] is True


@pytest.mark.asyncio
async def test_correct_field_recalculates_confidence_and_validations(async_client: AsyncClient, seeded_data: dict, db_session):
    """Correction uses document's real type and recalculates confidence and validations."""
    reviewer_token = seeded_data["reviewer_token"]
    tenant_id = seeded_data["tenant_1"].id
    headers = {"Authorization": f"Bearer {reviewer_token}"}

    # Create Trade License document type
    trade_license_dt = DocumentType(
        tenant_id=tenant_id,
        code="uae_trade_license",
        name_en="Commercial Trade License",
        name_ar="رخصة تجارية",
        schema_definition={
            "fields": [
                {"key": "license_number", "required": True, "confidence_threshold": 0.85},
                {"key": "company_name_en", "required": True, "confidence_threshold": 0.85}
            ]
        },
        is_active=True
    )
    db_session.add(trade_license_dt)
    await db_session.flush()

    doc = Document(
        tenant_id=tenant_id,
        document_type_id=trade_license_dt.id,
        file_name="license.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://license.png",
        status="needs_review",
        confidence_score=0.40
    )
    db_session.add(doc)
    await db_session.flush()

    field_lic = ExtractedField(
        tenant_id=tenant_id,
        document_id=doc.id,
        field_name="license_number",
        value=None,
        raw_value="",
        confidence=0.0,
        page_number=1
    )
    field_name = ExtractedField(
        tenant_id=tenant_id,
        document_id=doc.id,
        field_name="company_name_en",
        value="Al Hilal Capital LLC",
        raw_value="Al Hilal Capital LLC",
        confidence=0.90,
        page_number=1
    )
    db_session.add_all([field_lic, field_name])
    await db_session.commit()

    # Correct license_number
    res = await async_client.patch(
        f"/api/v1/documents/{doc.id}/fields/license_number",
        headers=headers,
        json={"corrected_value": "TL-998877", "reason": "manual entry"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["value"] == "TL-998877"
    assert data["is_corrected"] is True
    assert data["confidence"] == 1.0

    # Verify doc overall confidence was recalculated: (1.0 + 0.90) / 2 = 0.95
    await db_session.refresh(doc)
    assert doc.confidence_score == 0.95


@pytest.mark.asyncio
async def test_arabic_filename_content_disposition_no_crash(async_client: AsyncClient, seeded_data: dict, db_session, monkeypatch):
    """Content-Disposition with filename*=UTF-8'' so Arabic filenames don't crash Latin-1 header encoding."""
    admin_token = seeded_data["admin_token"]
    tenant_id = seeded_data["tenant_1"].id
    headers = {"Authorization": f"Bearer {admin_token}"}

    arabic_filename = "بطاقة_هوية_إماراتية_أحمد.png"
    doc = Document(
        tenant_id=tenant_id,
        file_name=arabic_filename,
        file_size=1024,
        mime_type="image/png",
        storage_path="local://arabic_test.png",
        status="approved"
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    with patch("app.api.v1.documents.storage_service.get_document_bytes", return_value=b"\x89PNG\r\n\x1a\nfake"):
        res = await async_client.get(f"/api/v1/documents/{doc.id}/file", headers=headers)
        assert res.status_code == 200
        cd = res.headers.get("content-disposition", "")
        assert "filename*=" in cd
        assert "UTF-8''" in cd


@pytest.mark.asyncio
async def test_upload_size_check_and_unknown_doc_type(async_client: AsyncClient, seeded_data: dict, monkeypatch):
    """Upload: check size while reading; 400 on unknown document_type_code."""
    admin_token = seeded_data["admin_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. 400 on unknown document_type_code
    files = {"file": ("test.png", io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50), "image/png")}
    data = {"document_type_code": "non_existent_type_code_xyz"}
    res_bad_type = await async_client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert res_bad_type.status_code == 400
    assert "Unknown document_type_code" in res_bad_type.json()["detail"]

    # 2. 413 on size exceeding limit
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)  # 1MB limit
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * (2 * 1024 * 1024))  # 2MB
    files_over = {"file": ("large.png", io.BytesIO(oversized_bytes), "image/png")}
    res_over = await async_client.post("/api/v1/documents/upload", headers=headers, files=files_over)
    assert res_over.status_code == 413


@pytest.mark.asyncio
async def test_document_type_code_in_list_and_detail(async_client: AsyncClient, seeded_data: dict, db_session):
    """Return document_type_code in list/detail."""
    admin_token = seeded_data["admin_token"]
    tenant_id = seeded_data["tenant_1"].id
    headers = {"Authorization": f"Bearer {admin_token}"}

    dt = DocumentType(
        tenant_id=tenant_id,
        code="custom_contract",
        name_en="Contract Document",
        name_ar="عقد رسمي",
        schema_definition={"fields": []},
        is_active=True
    )
    db_session.add(dt)
    await db_session.flush()

    doc = Document(
        tenant_id=tenant_id,
        document_type_id=dt.id,
        file_name="contract_doc.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://contract_doc.png",
        status="approved"
    )
    db_session.add(doc)
    await db_session.commit()

    # Detail
    detail_res = await async_client.get(f"/api/v1/documents/{doc.id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["document_type_code"] == "custom_contract"

    # List
    list_res = await async_client.get(f"/api/v1/documents?document_type_code=custom_contract", headers=headers)
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    assert len(docs) > 0
    assert docs[0]["document_type_code"] == "custom_contract"


@pytest.mark.asyncio
async def test_user_management_patch_delete_and_last_admin_guard(async_client: AsyncClient, seeded_data: dict, db_session):
    """PATCH/DELETE /users/{id} (can't remove last admin); tenant-scoped, audited."""
    admin_token = seeded_data["admin_token"]
    tenant_id = seeded_data["tenant_1"].id
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create reviewer user
    reviewer = User(
        tenant_id=tenant_id,
        email="extra_reviewer@adcb.ae",
        hashed_password=hash_password("Pass123!"),
        full_name="Extra Reviewer",
        role="reviewer",
        is_active=True
    )
    db_session.add(reviewer)
    await db_session.commit()
    await db_session.refresh(reviewer)

    # 1. PATCH reviewer to change name
    patch_res = await async_client.patch(
        f"/api/v1/users/{reviewer.id}",
        headers=admin_headers,
        json={"full_name": "Updated Reviewer Name"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Updated Reviewer Name"

    # 2. DELETE reviewer succeeds
    del_res = await async_client.delete(f"/api/v1/users/{reviewer.id}", headers=admin_headers)
    assert del_res.status_code == 200

    # 3. Cannot delete or demote last admin
    admin_user = seeded_data["admin_user"]
    del_admin_res = await async_client.delete(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
    assert del_admin_res.status_code == 400
    assert "last remaining admin" in del_admin_res.json()["detail"].lower()

    demote_admin_res = await async_client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=admin_headers,
        json={"role": "viewer"}
    )
    assert demote_admin_res.status_code == 400
    assert "last remaining admin" in demote_admin_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_document_types_put_and_delete(async_client: AsyncClient, seeded_data: dict, db_session):
    """PUT/DELETE /document-types/{id}; tenant-scoped, audited."""
    admin_token = seeded_data["admin_token"]
    tenant_id = seeded_data["tenant_1"].id
    headers = {"Authorization": f"Bearer {admin_token}"}

    dt = DocumentType(
        tenant_id=tenant_id,
        code="temp_type",
        name_en="Temp Type En",
        name_ar="نوع مؤقت",
        schema_definition={"fields": []},
        is_active=True
    )
    db_session.add(dt)
    await db_session.commit()
    await db_session.refresh(dt)

    # PUT
    put_res = await async_client.put(
        f"/api/v1/document-types/{dt.id}",
        headers=headers,
        json={"name_en": "Updated Type En", "description": "New description"}
    )
    assert put_res.status_code == 200
    assert put_res.json()["name_en"] == "Updated Type En"

    # DELETE
    del_res = await async_client.delete(f"/api/v1/document-types/{dt.id}", headers=headers)
    assert del_res.status_code == 200

    # Re-fetch should be 404
    get_res = await async_client.put(
        f"/api/v1/document-types/{dt.id}",
        headers=headers,
        json={"name_en": "Should Fail"}
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_stuck_job_sweeper_handles_queued_and_processing(db_session, seeded_data):
    """Schedule stuck-job sweeper every minute (also 'queued' > 15 min)."""
    tenant_id = seeded_data["tenant_1"].id
    now = datetime.now(timezone.utc)

    # 1. Stuck processing job (older than 5 min)
    doc_stuck_proc = Document(
        tenant_id=tenant_id,
        file_name="stuck_proc.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://stuck_proc.png",
        status="processing",
        updated_at=now - timedelta(minutes=10)
    )
    # 2. Stuck queued job (older than 15 min)
    doc_stuck_queued = Document(
        tenant_id=tenant_id,
        file_name="stuck_queued.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://stuck_queued.png",
        status="queued",
        created_at=now - timedelta(minutes=20)
    )
    # 3. Healthy fresh queued job (< 5 min)
    doc_fresh_queued = Document(
        tenant_id=tenant_id,
        file_name="fresh_queued.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://fresh_queued.png",
        status="queued",
        created_at=now - timedelta(minutes=2)
    )
    db_session.add_all([doc_stuck_proc, doc_stuck_queued, doc_fresh_queued])
    await db_session.commit()

    swept = await sweep_stuck_jobs(db_session, timeout_seconds=300, queued_timeout_minutes=15)
    assert swept >= 2

    await db_session.refresh(doc_stuck_proc)
    await db_session.refresh(doc_stuck_queued)
    await db_session.refresh(doc_fresh_queued)

    assert doc_stuck_proc.status == "failed"
    assert doc_stuck_queued.status == "failed"
    assert doc_fresh_queued.status == "queued"
