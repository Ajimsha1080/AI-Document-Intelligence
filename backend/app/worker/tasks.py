import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import AsyncSessionLocal
from app.models.document import Document, ExtractedField, DocumentPage, ValidationResult
from app.models.document_type import DocumentType
from app.services.storage_service import storage_service
from app.services.model_engine.factory import get_model_provider
from app.pipeline.preprocessor import ImagePreprocessor
from app.pipeline.validator import run_validation_rules
from app.services.audit_service import log_audit_event

logger = logging.getLogger("worker_task")

async def _run_pipeline_core(document_id: str, tenant_id: str, db: AsyncSession) -> Document:
    stmt = select(Document).where(and_(Document.id == document_id, Document.tenant_id == tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        logger.error(f"Worker task error: Document {document_id} for tenant {tenant_id} not found.")
        return None

    # 1. Update status to processing
    doc.status = "processing"
    await db.commit()

    try:
        # 2. Retrieve document bytes
        raw_bytes = storage_service.get_document_bytes(doc.storage_path)

        # 3. Preprocess image
        processed_bytes, prep_meta = ImagePreprocessor.preprocess_image(raw_bytes)

        # 4. Resolve document type
        doc_type_code = "emirates_id"
        schema_def = {}
        if doc.document_type_id:
            dt_stmt = select(DocumentType).where(DocumentType.id == doc.document_type_id)
            dt_res = await db.execute(dt_stmt)
            dt = dt_res.scalar_one_or_none()
            if dt:
                doc_type_code = dt.code
                schema_def = dt.schema_definition or {}

        # 5. Execute model provider
        provider = get_model_provider()
        extraction_res = await provider.extract_fields(
            document_bytes=processed_bytes,
            document_type_code=doc_type_code,
            schema_definition=schema_def
        )

        # 6. Save pages
        for p in extraction_res.pages:
            page_row = DocumentPage(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                page_number=p.page_number,
                image_path=doc.storage_path,
                width=p.width,
                height=p.height
            )
            db.add(page_row)

        # 7. Save extracted fields
        has_missing_or_low_conf = False
        for ef in extraction_res.fields:
            bbox_dict = ef.bounding_box.model_dump() if ef.bounding_box else None
            field_row = ExtractedField(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                field_name=ef.field_name,
                value=ef.value,
                raw_value=ef.raw_value,
                confidence=ef.confidence,
                page_number=ef.page_number,
                bounding_box=bbox_dict
            )
            db.add(field_row)
            if ef.value is None or ef.confidence < 0.85:
                has_missing_or_low_conf = True

        # 8. Run validation engine
        val_outcomes = run_validation_rules(
            document_type_code=doc_type_code,
            fields=extraction_res.fields,
            schema_definition=schema_def
        )

        has_validation_errors = False
        for vo in val_outcomes:
            val_row = ValidationResult(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                rule_name=vo["rule_name"],
                passed=vo["passed"],
                severity=vo["severity"],
                message=vo["message"]
            )
            db.add(val_row)
            if not vo["passed"] and vo["severity"] == "error":
                has_validation_errors = True

        # 9. Set final document status
        doc.confidence_score = extraction_res.overall_confidence
        if has_validation_errors or has_missing_or_low_conf:
            doc.status = "needs_review"
        else:
            doc.status = "approved"

        await log_audit_event(
            db=db,
            tenant_id=doc.tenant_id,
            actor_id="system_worker",
            actor_email="worker@pipeline.local",
            actor_role="system",
            action="DOCUMENT_PROCESSED",
            entity_type="document",
            entity_id=doc.id,
            details={
                "status": doc.status,
                "confidence": doc.confidence_score,
                "validation_errors": has_validation_errors,
                "backend_used": getattr(provider, "backend_name", "local")
            }
        )
        await db.commit()
        await db.refresh(doc)
        return doc

    except Exception as e:
        logger.exception(f"Pipeline error processing document {document_id}: {e}")
        doc.status = "failed"
        await log_audit_event(
            db=db,
            tenant_id=doc.tenant_id,
            actor_id="system_worker",
            actor_email="worker@pipeline.local",
            actor_role="system",
            action="DOCUMENT_PROCESS_FAILED",
            entity_type="document",
            entity_id=doc.id,
            details={"error": str(e)}
        )
        await db.commit()
        await db.refresh(doc)
        return doc

async def process_document_pipeline(
    document_id: str,
    tenant_id: str,
    db: Optional[AsyncSession] = None
) -> Document:
    """
    End-to-end extraction pipeline execution:
    If db session is provided (e.g. testing context), uses it;
    otherwise opens an AsyncSessionLocal().
    """
    if db is not None:
        return await _run_pipeline_core(document_id, tenant_id, db)
    async with AsyncSessionLocal() as session:
        return await _run_pipeline_core(document_id, tenant_id, session)
