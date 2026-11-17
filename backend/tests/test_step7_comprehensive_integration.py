import io
import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from PIL import Image
from app.models.document import Document, ExtractedField, DocumentPage, ValidationResult
from app.models.audit import AuditLog
from app.worker.tasks import process_document_pipeline
from app.services.retention_service import run_retention_policy_sweep

def _create_test_png():
    sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "eval", "dataset", "sample_001.png"))
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            return f.read()
    buf = io.BytesIO()
    img = Image.new("RGB", (1000, 630), color=(240, 244, 248))
    img.save(buf, format="PNG")
    return buf.getvalue()

SYNTHETIC_EID_PNG = _create_test_png()

@pytest.mark.asyncio
async def test_invalid_and_oversized_file_rejection(async_client: AsyncClient, seeded_data: dict):
    """Step 7: Validates rejection of spoofed extensions and oversized files."""
    token = seeded_data["admin_token"]

    # 1. Reject binary disguised as image (e.g. MZ Windows Executable)
    spoofed_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
    files = {"file": ("malware.png", io.BytesIO(spoofed_bytes), "image/png")}
    res = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    assert res.status_code == 400
    assert "Unsupported or invalid file format" in res.json()["detail"]

    # 2. Reject oversized file (> 25MB)
    oversized_bytes = b"%PDF-1.4\n" + b"0" * (26 * 1024 * 1024)
    files_big = {"file": ("huge.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    res_big = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files_big
    )
    assert res_big.status_code == 413
    assert "exceeds maximum permissible size" in res_big.json()["detail"]

    # 3. Reject SVG uploads strictly
    svg_bytes = b"<svg xmlns='http://www.w3.org/2000/svg'><text>Forbidden SVG</text></svg>"
    res_svg = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("vector.svg", io.BytesIO(svg_bytes), "image/svg+xml")}
    )
    assert res_svg.status_code == 400
    assert "SVG files are not permitted" in res_svg.json()["detail"]

    # 4. Reject file with fake extension (PNG bytes uploaded with .pdf extension)
    res_fake_ext = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("spoofed.pdf", io.BytesIO(SYNTHETIC_EID_PNG), "application/pdf")}
    )
    assert res_fake_ext.status_code == 400
    assert "extension" in res_fake_ext.json()["detail"].lower()

    # 5. Reject malformed PDF
    malformed_pdf = b"%PDF-1.5\nMalformed truncated content without trailer"
    res_malformed = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corrupt.pdf", io.BytesIO(malformed_pdf), "application/pdf")}
    )
    assert res_malformed.status_code == 400
    assert "PDF" in res_malformed.json()["detail"]


@pytest.mark.asyncio
async def test_pdf_rasterization_before_ocr():
    """Step 4: Verifies that PDFs are rasterized to pixel images before OCR."""
    from app.pipeline.preprocessor import ImagePreprocessor

    buf = io.BytesIO()
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    img.save(buf, format="PDF")
    pdf_bytes = buf.getvalue()

    processed_bytes, meta = ImagePreprocessor.preprocess_image(pdf_bytes)
    assert meta.get("rasterized_pdf") is True
    assert processed_bytes.startswith(b"\x89PNG")

@pytest.mark.asyncio
async def test_tenant_isolation_across_all_lifecycle_endpoints(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Step 7: Enforces strict multi-tenant barrier.
    Tenant 2 cannot view, stream, correct fields, approve, reject, export, or delete Tenant 1's document.
    """
    tenant1 = seeded_data["tenant_1"]
    tenant2 = seeded_data["tenant_2"]
    t1_token = seeded_data["admin_token"]
    t2_token = seeded_data["tenant2_token"]

    # 1. Tenant 1 uploads document
    files = {"file": ("t1_isolated_doc.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {t1_token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    await process_document_pipeline(doc_id, tenant1.id, db=db_session)

    # 2. Tenant 2 attempts GET details -> 404
    t2_get = await async_client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {t2_token}"}
    )
    assert t2_get.status_code == 404

    # 3. Tenant 2 attempts GET file stream -> 404
    t2_file = await async_client.get(
        f"/api/v1/documents/{doc_id}/file",
        headers={"Authorization": f"Bearer {t2_token}"}
    )
    assert t2_file.status_code == 404

    # 4. Tenant 2 attempts PATCH field -> 404
    t2_patch = await async_client.patch(
        f"/api/v1/documents/{doc_id}/fields/id_number",
        headers={"Authorization": f"Bearer {t2_token}"},
        json={"corrected_value": "784-1988-1234567-9"}
    )
    assert t2_patch.status_code == 404

    # 5. Tenant 2 attempts POST approve -> 404
    t2_appr = await async_client.post(
        f"/api/v1/documents/{doc_id}/approve",
        headers={"Authorization": f"Bearer {t2_token}"}
    )
    assert t2_appr.status_code == 404

    # 6. Tenant 2 attempts POST reject -> 404
    t2_rej = await async_client.post(
        f"/api/v1/documents/{doc_id}/reject",
        headers={"Authorization": f"Bearer {t2_token}"},
        json={"rejection_reason": "Tenant 2 interference"}
    )
    assert t2_rej.status_code == 404

    # 7. Tenant 2 attempts GET export -> 404
    t2_exp = await async_client.get(
        f"/api/v1/documents/{doc_id}/export",
        headers={"Authorization": f"Bearer {t2_token}"}
    )
    assert t2_exp.status_code == 404

    # 8. Tenant 2 attempts DELETE -> 404
    t2_del = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {t2_token}"}
    )
    assert t2_del.status_code == 404

@pytest.mark.asyncio
async def test_hard_delete_removes_all_derived_data_and_leaves_audit_record(
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Step 7: Deleting a document hard-deletes original file, extracted fields,
    pages, and validation results, leaving only an immutable DOCUMENT_DELETE audit event.
    """
    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    # 1. Upload & process
    files = {"file": ("doc_for_deletion.png", io.BytesIO(SYNTHETIC_EID_PNG), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    doc_id = up.json()["id"]
    await process_document_pipeline(doc_id, tenant.id, db=db_session)

    # Verify derived records exist
    f_res = await db_session.execute(select(ExtractedField).where(ExtractedField.document_id == doc_id))
    assert len(f_res.scalars().all()) >= 5

    # 2. Execute Hard Delete
    del_res = await async_client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200

    # 3. Assert all derived rows are wiped from database
    from app.models.document_chunk import DocumentChunk
    c_after = await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    assert len(c_after.scalars().all()) == 0

    f_after = await db_session.execute(select(ExtractedField).where(ExtractedField.document_id == doc_id))
    assert len(f_after.scalars().all()) == 0

    v_after = await db_session.execute(select(ValidationResult).where(ValidationResult.document_id == doc_id))
    assert len(v_after.scalars().all()) == 0

    p_after = await db_session.execute(select(DocumentPage).where(DocumentPage.document_id == doc_id))
    assert len(p_after.scalars().all()) == 0

    d_after = await db_session.execute(select(Document).where(Document.id == doc_id))
    assert d_after.scalar_one_or_none() is None

    # 4. Assert immutable audit log remains
    audit_res = await async_client.get(
        "/api/v1/audit/",
        headers={"Authorization": f"Bearer {token}"},
        params={"action": "DOCUMENT_DELETE"}
    )
    assert audit_res.status_code == 200
    assert any(log["entity_id"] == doc_id for log in audit_res.json())
