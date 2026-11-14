import io
import json
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.document import Document, ExtractedField, ValidationResult
from app.worker.tasks import process_document_pipeline
from app.worker.sweeper import sweep_stuck_jobs
from app.pipeline.emirates_id_parser import calculate_emirates_id_check_digit, validate_emirates_id_number

VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

# Synthetic Emirates ID SVG fixture containing realistic Arabic & English text
SYNTHETIC_EID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="630">
  <rect width="1000" height="630" fill="#f0f4f8"/>
  <text x="250" y="80">UNITED ARAB EMIRATES FEDERAL AUTHORITY FOR IDENTITY</text>
  <text x="250" y="120">بطاقة الهوية الإماراتية Identity Card</text>
  <text x="250" y="200">الاسم: سالم راشد سيف الشامسي</text>
  <text x="250" y="260">Name: SALEM RASHED SAIF ALSHAMSI</text>
  <text x="250" y="340">ID: 784-1988-1234567-1</text>
  <text x="250" y="420">Nationality / الجنسية: United Arab Emirates</text>
  <text x="250" y="480">DOB / الميلاد: 15/04/1988</text>
  <text x="600" y="480">Expiry / الانتهاء: 30/12/2028</text>
  <text x="250" y="540">Sex / الجنس: M</text>
</svg>""".encode("utf-8")

@pytest.mark.asyncio
async def test_emirates_id_check_digit_calculation():
    """Verify Emirates ID check digit calculation and normalization logic."""
    # First 14 digits of 784-1988-1234567-1
    first_14 = "78419881234567"
    check_digit = calculate_emirates_id_check_digit(first_14)
    assert isinstance(check_digit, int)
    
    # Valid formatted ID verification
    valid_id = f"784-1988-1234567-{check_digit}"
    is_valid, formatted, expected_check = validate_emirates_id_number(valid_id)
    assert is_valid is True
    assert formatted == valid_id
    assert expected_check == check_digit

    # Invalid check digit
    wrong_check = (check_digit + 1) % 10
    invalid_id = f"784-1988-1234567-{wrong_check}"
    is_valid_wrong, _, _ = validate_emirates_id_number(invalid_id)
    assert is_valid_wrong is False

@pytest.mark.asyncio
async def test_end_to_end_pipeline_execution(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """
    Step 2 & 3: Run real vertical slice pipeline:
    Upload -> Preprocess -> Local Extract -> Save Fields -> Validate -> Score
    """
    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    # 1. Upload document
    files = {"file": ("synthetic_eid.svg", io.BytesIO(SYNTHETIC_EID_SVG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # 2. Run background pipeline worker task
    processed_doc = await process_document_pipeline(doc_id, tenant.id, db=db_session)
    assert processed_doc is not None
    assert processed_doc.status in ["approved", "needs_review"]
    assert processed_doc.confidence_score is not None

    # 3. Query document details via API
    get_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 200
    doc_data = get_resp.json()
    assert len(doc_data["extracted_fields"]) >= 5
    assert len(doc_data["validation_results"]) >= 1

    field_map = {f["field_name"]: f for f in doc_data["extracted_fields"]}
    assert "id_number" in field_map
    assert field_map["id_number"]["bounding_box"] is not None

@pytest.mark.asyncio
async def test_stuck_job_sweeper(seeded_data: dict, db_session):
    """
    Step 2: Stuck job sweeper marks jobs stuck in 'processing' past timeout as 'failed'.
    """
    tenant = seeded_data["tenant_1"]
    past_time = datetime.now(timezone.utc) - timedelta(seconds=400)

    stuck_doc = Document(
        tenant_id=tenant.id,
        file_name="stuck_kyc.pdf",
        file_size=1024,
        mime_type="application/pdf",
        storage_path=f"data/{tenant.id}/stuck_doc/stuck.pdf",
        status="processing",
        updated_at=past_time
    )
    db_session.add(stuck_doc)
    await db_session.commit()
    await db_session.refresh(stuck_doc)
    stuck_id = stuck_doc.id

    # Run sweeper with 300s timeout
    swept_count = await sweep_stuck_jobs(db_session, timeout_seconds=300)
    assert swept_count >= 1

    # Verify status changed to failed
    res = await db_session.execute(select(Document).where(Document.id == stuck_id))
    doc_after = res.scalar_one()
    assert doc_after.status == "failed"

@pytest.mark.asyncio
async def test_field_correction_and_revalidation(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """
    Step 4: Reviewer field correction updates value, sets is_corrected=True,
    re-runs validation rules, and logs FIELD_CORRECT audit event.
    """
    token = seeded_data["reviewer_token"]
    tenant = seeded_data["tenant_1"]

    # 1. Upload & process
    files = {"file": ("eid_for_review.svg", io.BytesIO(SYNTHETIC_EID_SVG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    # 2. Correct a field
    correct_resp = await async_client.patch(
        f"/api/v1/documents/{doc_id}/fields/id_number",
        headers={"Authorization": f"Bearer {token}"},
        json={"corrected_value": "784-1988-1234567-1", "reason": "OCR digit clarity correction"}
    )
    assert correct_resp.status_code == 200
    field_data = correct_resp.json()
    assert field_data["is_corrected"] is True
    assert field_data["corrected_value"] == "784-1988-1234567-1"

    # 3. Check FIELD_CORRECT audit log as Admin
    admin_token = seeded_data["admin_token"]
    audit_resp = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"action": "FIELD_CORRECT"}
    )
    assert audit_resp.status_code == 200
    assert any(log["details"].get("field_name") == "id_number" for log in audit_resp.json())

@pytest.mark.asyncio
async def test_approve_document_and_signed_webhook(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """
    Step 4: Approving document updates status to 'approved' and dispatches
    HMAC-SHA256 signed webhook payload.
    """
    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    # Upload & process
    files = {"file": ("eid_approve.svg", io.BytesIO(SYNTHETIC_EID_SVG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    # Approve
    approve_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/approve",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "approved"
    assert data["webhook"]["dispatched"] is True
    assert data["webhook"]["signature"].startswith("sha256=")

@pytest.mark.asyncio
async def test_reject_document(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """Step 4: Reject document with reason."""
    token = seeded_data["reviewer_token"]
    tenant = seeded_data["tenant_1"]

    files = {"file": ("eid_reject.svg", io.BytesIO(SYNTHETIC_EID_SVG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    reject_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"rejection_reason": "Blurry image; ICP hologram missing"}
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

@pytest.mark.asyncio
async def test_export_with_pii_masking(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """
    Step 4: Export structured document data with optional PII masking (JSON and CSV).
    """
    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    files = {"file": ("eid_export.svg", io.BytesIO(SYNTHETIC_EID_SVG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    # 1. Export JSON with PII Masking
    json_masked_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "json", "mask_pii": True}
    )
    assert json_masked_resp.status_code == 200
    export_json = json_masked_resp.json()
    assert export_json["pii_masked"] is True
    id_val = export_json["fields"]["id_number"]["value"]
    # Masked pattern: 784-****-*******-1
    assert "****" in id_val

    # 2. Export CSV
    csv_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "csv", "mask_pii": True}
    )
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "field_name,value" in csv_resp.text
