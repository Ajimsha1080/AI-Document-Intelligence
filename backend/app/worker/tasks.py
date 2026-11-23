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
from app.services.event_bus import event_bus
import time

logger = logging.getLogger("worker_task")

async def _run_pipeline_core(document_id: str, tenant_id: str, db: AsyncSession) -> Document:
    stmt = select(Document).where(and_(Document.id == document_id, Document.tenant_id == tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        logger.error(f"Worker task error: Document {document_id} for tenant {tenant_id} not found.")
        return None

    # 1. Update status to processing and emit preprocessing event
    doc.status = "processing"
    await db.commit()
    t_start = time.perf_counter()

    await event_bus.emit_event(
        tenant_id=tenant_id,
        document_id=document_id,
        stage="preprocessing",
        status="processing",
        stage_duration_ms=0.0,
        progress_pct=15,
        details={"file_name": doc.file_name}
    )

    try:
        # 2. Retrieve document bytes
        raw_bytes = storage_service.get_document_bytes(doc.storage_path)

        # 3. Preprocess image or handle multi-page PDF
        t_prep_start = time.perf_counter()
        is_pdf = raw_bytes.startswith(b"%PDF")
        if is_pdf:
            processed_bytes = raw_bytes
            prep_meta = {"is_pdf": True}
        else:
            processed_bytes, prep_meta = ImagePreprocessor.preprocess_image(raw_bytes)
        prep_ms = (time.perf_counter() - t_prep_start) * 1000

        # 4. Resolve document type
        provider = get_model_provider()
        doc_type_code = None
        schema_def = {}
        if doc.document_type_id:
            dt_stmt = select(DocumentType).where(DocumentType.id == doc.document_type_id)
            dt_res = await db.execute(dt_stmt)
            dt = dt_res.scalar_one_or_none()
            if dt:
                doc_type_code = dt.code
                schema_def = dt.schema_definition or {}

        if not doc_type_code:
            classification = await provider.classify_document(processed_bytes, doc.file_name)
            doc_type_code = classification.document_type_code
            doc.language_detected = classification.language
            if doc_type_code != "unknown":
                dt_stmt = select(DocumentType).where(
                    and_(DocumentType.tenant_id == doc.tenant_id, DocumentType.code == doc_type_code)
                )
                dt_res = await db.execute(dt_stmt)
                matching_dt = dt_res.scalar_one_or_none()
                if matching_dt:
                    doc.document_type_id = matching_dt.id
                    schema_def = matching_dt.schema_definition or {}
        else:
            classification = await provider.classify_document(processed_bytes, doc.file_name)
            doc.language_detected = classification.language

        if doc_type_code == "unknown":
            doc.status = "needs_review"
            doc.confidence_score = 0.30
            from sqlalchemy import delete
            await db.execute(delete(ValidationResult).where(ValidationResult.document_id == doc.id))
            await db.flush()
            val_row = ValidationResult(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                rule_name="document_type_classification",
                passed=False,
                severity="error",
                message="Unrecognized document type. Routed to manual review."
            )
            db.add(val_row)
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
                    "status": "needs_review",
                    "confidence": 0.30,
                    "validation_errors": True,
                    "reason": "Unrecognized document type"
                }
            )
            await db.commit()
            await db.refresh(doc)

            # Emit terminal needs_review event
            total_ms = (time.perf_counter() - t_start) * 1000
            await event_bus.emit_event(
                tenant_id=tenant_id,
                document_id=document_id,
                stage="needs_review",
                status="needs_review",
                stage_duration_ms=total_ms,
                progress_pct=100,
                details={"reason": "Unrecognized document type"}
            )
            return doc

        # 5. Emit OCR Stage Event
        await event_bus.emit_event(
            tenant_id=tenant_id,
            document_id=document_id,
            stage="ocr",
            status="processing",
            stage_duration_ms=prep_ms,
            progress_pct=40,
            details={"document_type": doc_type_code}
        )

        # 6. Execute model provider
        t_ocr_start = time.perf_counter()
        extraction_res = await provider.extract_fields(
            document_bytes=processed_bytes,
            document_type_code=doc_type_code,
            schema_definition=schema_def
        )
        ocr_ms = (time.perf_counter() - t_ocr_start) * 1000

        # 7. Emit Parsing Stage Event
        await event_bus.emit_event(
            tenant_id=tenant_id,
            document_id=document_id,
            stage="parsing",
            status="processing",
            stage_duration_ms=ocr_ms,
            progress_pct=70,
            details={"fields_extracted": len(extraction_res.fields)}
        )

        # 8. Clean up old records before saving new ones (idempotent / retry safe)
        from sqlalchemy import delete
        from app.models.document_chunk import DocumentChunk
        await db.execute(delete(ExtractedField).where(ExtractedField.document_id == doc.id))
        await db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        await db.execute(delete(ValidationResult).where(ValidationResult.document_id == doc.id))
        await db.flush()

        # 9. Save pages
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

        # 9. Save extracted fields
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

        # Generate layout-aware document chunks for Sovereign RAG
        from app.models.document_chunk import DocumentChunk
        from app.services.rag.chunker import chunk_document_tokens, chunk_text_fallback
        from app.services.rag.providers import get_default_embedding_provider

        embedder = get_default_embedding_provider()
        all_chunks_data = []

        for p in extraction_res.pages:
            p_tokens = getattr(p, "blocks", []) or []
            if p_tokens:
                p_chunks = chunk_document_tokens(p_tokens, target_chunk_tokens=40, page_number=p.page_number)
                all_chunks_data.extend(p_chunks)

        if not all_chunks_data:
            field_lines = [f"{f.field_name}: {f.value}" for f in extraction_res.fields if f.value]
            all_chunks_data = chunk_text_fallback(" \n ".join(field_lines), target_words=30, page_number=1)

        for ch in all_chunks_data:
            chunk_embedding = embedder.embed_query(ch["chunk_text"])
            db_chunk = DocumentChunk(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                page_number=ch["page_number"],
                chunk_index=ch["chunk_index"],
                chunk_text=ch["chunk_text"],
                chunk_text_normalized=ch["chunk_text_normalized"],
                bounding_box=ch["bounding_box"],
                embedding=chunk_embedding,
                token_count=ch["token_count"]
            )
            db.add(db_chunk)

        # 10. Emit Validating Stage Event
        t_val_start = time.perf_counter()
        parse_ms = (t_val_start - t_ocr_start) * 1000 - ocr_ms
        await event_bus.emit_event(
            tenant_id=tenant_id,
            document_id=document_id,
            stage="validating",
            status="processing",
            stage_duration_ms=round(max(0.1, parse_ms), 2),
            progress_pct=85
        )

        # 11. Run validation engine
        val_outcomes = run_validation_rules(
            document_type_code=doc_type_code,
            fields=extraction_res.fields,
            schema_definition=schema_def
        )
        val_ms = (time.perf_counter() - t_val_start) * 1000

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

        # 12. Set final document status
        doc.confidence_score = extraction_res.overall_confidence
        if has_validation_errors or has_missing_or_low_conf:
            doc.status = "needs_review"
            terminal_stage = "needs_review"
        else:
            doc.status = "approved"
            terminal_stage = "approved"
            try:
                from app.services.webhook_service import dispatch_document_approved_webhook
                fields_dict = {f.field_name: f.value for f in extraction_res.fields}
                await dispatch_document_approved_webhook(
                    tenant_id=doc.tenant_id,
                    document_id=doc.id,
                    document_data={
                        "file_name": doc.file_name,
                        "status": "approved",
                        "confidence_score": doc.confidence_score,
                        "extracted_fields": fields_dict
                    }
                )
            except Exception as wh_err:
                logger.warning(f"Auto-approve webhook dispatch encountered error: {wh_err}")

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

        # 13. Emit terminal stage event
        total_ms = (time.perf_counter() - t_start) * 1000
        await event_bus.emit_event(
            tenant_id=tenant_id,
            document_id=document_id,
            stage=terminal_stage,
            status=doc.status,
            stage_duration_ms=val_ms,
            progress_pct=100,
            details={
                "total_processing_ms": round(total_ms, 2),
                "confidence": doc.confidence_score,
                "has_validation_errors": has_validation_errors
            }
        )
        return doc

    except Exception as e:
        logger.exception(f"Pipeline error processing document {document_id}: {e}")
        await db.rollback()
        try:
            stmt = select(Document).where(and_(Document.id == document_id, Document.tenant_id == tenant_id))
            res = await db.execute(stmt)
            failed_doc = res.scalar_one_or_none()
            if failed_doc:
                failed_doc.status = "failed"
                await log_audit_event(
                    db=db,
                    tenant_id=tenant_id,
                    actor_id="system_worker",
                    actor_email="worker@pipeline.local",
                    actor_role="system",
                    action="DOCUMENT_PROCESS_FAILED",
                    entity_type="document",
                    entity_id=document_id,
                    details={"error": str(e)}
                )
                await db.commit()
        except Exception as save_err:
            logger.error(f"Failed to record failed status in DB: {save_err}")
            await db.rollback()

        total_ms = (time.perf_counter() - t_start) * 1000 if 't_start' in locals() else 0.0
        await event_bus.emit_event(
            tenant_id=tenant_id,
            document_id=document_id,
            stage="failed",
            status="failed",
            stage_duration_ms=total_ms,
            progress_pct=100,
            details={"error": str(e)}
        )
        # Re-raise so RQ can retry
        raise

async def process_document_pipeline(
    document_id: str,
    tenant_id: str,
    db: Optional[AsyncSession] = None
) -> Document:
    """
    End-to-end extraction pipeline execution:
    If db session is provided (e.g. testing context), uses it;
    otherwise creates a worker engine with NullPool, runs the job, and disposes the engine cleanly.
    """
    if db is not None:
        return await _run_pipeline_core(document_id, tenant_id, db)

    from app.core.database import create_worker_engine, create_worker_sessionmaker
    worker_engine = create_worker_engine()
    worker_session_maker = create_worker_sessionmaker(worker_engine)
    try:
        async with worker_session_maker() as session:
            return await _run_pipeline_core(document_id, tenant_id, session)
    finally:
        await worker_engine.dispose()
