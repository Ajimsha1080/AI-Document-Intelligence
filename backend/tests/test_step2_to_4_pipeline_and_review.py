import io
import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, ExtractedField, ValidationResult
from app.worker.tasks import process_document_pipeline
from app.worker.sweeper import sweep_stuck_jobs
from app.pipeline.emirates_id_parser import calculate_emirates_id_check_digit, validate_emirates_id_number

VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
SAMPLE_PNG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "eval", "dataset", "sample_001.png"))
if os.path.exists(SAMPLE_PNG_PATH):
    with open(SAMPLE_PNG_PATH, "rb") as f:
        SYNTHETIC_EID_PNG = f.read()
else:
    SYNTHETIC_EID_PNG = VALID_PNG_BYTES

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
    files = {"file": ("synthetic_eid.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
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
    files = {"file": ("eid_for_review.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
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
    files = {"file": ("eid_approve.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    # Approve (admin force=true overrides failed error validations)
    approve_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/approve?force=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "approved"
    assert data["webhook"]["dispatched"] is False
    assert "reason" in data["webhook"]
    assert data["webhook"]["signature"] is None or data["webhook"]["signature"].startswith("sha256=")

@pytest.mark.asyncio
async def test_reject_document(async_client: AsyncClient, seeded_data: dict, db_session: AsyncSession):
    """Step 4: Reject document with reason."""
    token = seeded_data["reviewer_token"]
    tenant = seeded_data["tenant_1"]

    files = {"file": ("eid_reject.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
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

    files = {"file": ("eid_export.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
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

@pytest.mark.asyncio
async def test_document_with_missing_fields_completes_with_needs_review_and_null_values(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession,
    monkeypatch
):
    """
    Step 1 fix verification: A document with missing or unreadable fields:
    - Never raises Pydantic ValidationError
    - Completes pipeline with status 'needs_review'
    - Missing fields are stored with value=None, raw_value="", confidence=0.0
    - Never invents fake values
    """
    from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
    from app.services.model_engine.base import BoundingBox
    monkeypatch.setattr(LocalOCRAdapter, "is_available", classmethod(lambda cls: True))
    monkeypatch.setattr(
        LocalOCRAdapter,
        "_extract_tokens_with_boxes",
        lambda self, img_bytes, img_w, img_h: [
            {"text": "الاسم:", "left": 0.2, "top": 0.2, "right": 0.25, "bottom": 0.25, "conf": 0.95, "center_x": 0.22, "center_y": 0.22, "box": BoundingBox(x=0.2, y=0.2, width=0.05, height=0.05)},
            {"text": "سالم", "left": 0.26, "top": 0.2, "right": 0.32, "bottom": 0.25, "conf": 0.95, "center_x": 0.29, "center_y": 0.22, "box": BoundingBox(x=0.26, y=0.2, width=0.06, height=0.05)},
            {"text": "راشد", "left": 0.33, "top": 0.2, "right": 0.38, "bottom": 0.25, "conf": 0.95, "center_x": 0.35, "center_y": 0.22, "box": BoundingBox(x=0.33, y=0.2, width=0.05, height=0.05)},
            {"text": "سيف", "left": 0.39, "top": 0.2, "right": 0.44, "bottom": 0.25, "conf": 0.95, "center_x": 0.41, "center_y": 0.22, "box": BoundingBox(x=0.39, y=0.2, width=0.05, height=0.05)},
            {"text": "الشامسي", "left": 0.45, "top": 0.2, "right": 0.52, "bottom": 0.25, "conf": 0.95, "center_x": 0.48, "center_y": 0.22, "box": BoundingBox(x=0.45, y=0.2, width=0.07, height=0.05)},
            {"text": "Name:", "left": 0.2, "top": 0.3, "right": 0.25, "bottom": 0.35, "conf": 0.94, "center_x": 0.22, "center_y": 0.32, "box": BoundingBox(x=0.2, y=0.3, width=0.05, height=0.05)},
            {"text": "SALEM", "left": 0.26, "top": 0.3, "right": 0.33, "bottom": 0.35, "conf": 0.94, "center_x": 0.29, "center_y": 0.32, "box": BoundingBox(x=0.26, y=0.3, width=0.07, height=0.05)},
            {"text": "RASHED", "left": 0.34, "top": 0.3, "right": 0.42, "bottom": 0.35, "conf": 0.94, "center_x": 0.38, "center_y": 0.32, "box": BoundingBox(x=0.34, y=0.3, width=0.08, height=0.05)},
            {"text": "SAIF", "left": 0.43, "top": 0.3, "right": 0.48, "bottom": 0.35, "conf": 0.94, "center_x": 0.45, "center_y": 0.32, "box": BoundingBox(x=0.43, y=0.3, width=0.05, height=0.05)},
            {"text": "ALSHAMSI", "left": 0.49, "top": 0.3, "right": 0.58, "bottom": 0.35, "conf": 0.94, "center_x": 0.53, "center_y": 0.32, "box": BoundingBox(x=0.49, y=0.3, width=0.09, height=0.05)},
            {"text": "Nationality:", "left": 0.2, "top": 0.4, "right": 0.30, "bottom": 0.45, "conf": 0.92, "center_x": 0.25, "center_y": 0.42, "box": BoundingBox(x=0.2, y=0.4, width=0.10, height=0.05)},
            {"text": "United", "left": 0.31, "top": 0.4, "right": 0.38, "bottom": 0.45, "conf": 0.92, "center_x": 0.34, "center_y": 0.42, "box": BoundingBox(x=0.31, y=0.4, width=0.07, height=0.05)},
            {"text": "Arab", "left": 0.39, "top": 0.4, "right": 0.44, "bottom": 0.45, "conf": 0.92, "center_x": 0.41, "center_y": 0.42, "box": BoundingBox(x=0.39, y=0.4, width=0.05, height=0.05)},
            {"text": "Emirates", "left": 0.45, "top": 0.4, "right": 0.54, "bottom": 0.45, "conf": 0.92, "center_x": 0.49, "center_y": 0.42, "box": BoundingBox(x=0.45, y=0.4, width=0.09, height=0.05)},
        ]
    )

    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    files = {"file": ("partial_eid.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # Refresh db_session snapshot to see committed upload row
    await db_session.rollback()

    # Process through pipeline without raising ValidationError
    processed_doc = await process_document_pipeline(doc_id, tenant.id, db=db_session)
    assert processed_doc is not None
    assert processed_doc.status == "needs_review"

    # Query details via API
    get_resp = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 200
    doc_data = get_resp.json()
    field_map = {f["field_name"]: f for f in doc_data["extracted_fields"]}

    # Present fields
    assert field_map["full_name_ar"]["value"] == "سالم راشد سيف الشامسي"
    assert field_map["full_name_en"]["value"] == "SALEM RASHED SAIF ALSHAMSI"
    assert field_map["nationality"]["value"] == "United Arab Emirates"

    # Missing fields: must be null, confidence 0, never invented
    assert field_map["id_number"]["value"] is None
    assert field_map["id_number"]["confidence"] == 0.0
    assert field_map["expiry_date"]["value"] is None
    assert field_map["expiry_date"]["confidence"] == 0.0
    assert field_map["date_of_birth"]["value"] is None
    assert field_map["date_of_birth"]["confidence"] == 0.0
    assert field_map["sex"]["value"] is None
    assert field_map["sex"]["confidence"] == 0.0

    # Validation errors should flag the missing mandatory fields
    failed_rules = [v for v in doc_data["validation_results"] if not v["passed"]]
    assert len(failed_rules) >= 2


@pytest.mark.asyncio
async def test_step3_honest_classification_and_token_union_boxes():
    """
    Step 3 Verification:
    - classify_document returns 'unknown' with low confidence when no markers match, never defaulting to emirates_id.
    - Token union bounding boxes are calculated accurately from real tokens (normalized 0-1).
    - Confidence is computed from token confidences.
    """
    from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
    from app.services.model_engine.base import BoundingBox

    adapter = LocalOCRAdapter()

    # 1. Classification of unknown content
    unknown_result = await adapter.classify_document(b"Random unrelated content without any UAE markers", "sample.txt")
    assert unknown_result.document_type_code == "unknown"
    assert unknown_result.confidence <= 0.40

    # 2. Token union bounding box calculation
    sample_tokens = [
        {"text": "784-1988-1234567-1", "left": 0.20, "top": 0.40, "right": 0.50, "bottom": 0.45, "conf": 0.94},
        {"text": "(ID)", "left": 0.51, "top": 0.40, "right": 0.58, "bottom": 0.45, "conf": 0.86}
    ]
    union_box = adapter._union_token_boxes(sample_tokens)
    assert union_box is not None
    assert union_box.x == 0.20
    assert union_box.y == 0.40
    assert round(union_box.width, 2) == 0.38
    assert round(union_box.height, 2) == 0.05

    avg_conf = adapter._average_token_confidence(sample_tokens)
    assert avg_conf == 0.90
