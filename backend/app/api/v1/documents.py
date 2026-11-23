import io
import os
import re
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request, Response
from fastapi.responses import StreamingResponse
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.core.config import settings
from app.core.file_validator import validate_magic_bytes, validate_file_size
from app.core.rbac import Permission
from app.api.deps import (
    get_current_actor,
    require_permission,
    require_stream_permission,
    require_role,
    AuthenticatedActor
)
from app.models.document import Document, DocumentPage, ExtractedField, ValidationResult
from app.models.document_type import DocumentType
from app.models.tenant import Tenant
from app.core.security import mask_pii_value
from app.schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    ExtractedFieldResponse,
    FieldCorrectionRequest,
    RejectDocumentRequest
)
from app.services.storage_service import storage_service
from app.services.audit_service import log_audit_event
from app.services.retention_service import run_retention_policy_sweep

router = APIRouter(prefix="/documents", tags=["Documents Management"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type_code: Optional[str] = Form(None),
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_UPLOAD)),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests and stores business documents into sovereign S3 storage.
    Validates file content by magic bytes (PDF, JPG, PNG, TIFF) and size ceiling.
    Enforces tenant isolation and records immutable audit event.
    """
    # 1. Read and validate content (check size while reading chunks)
    chunk_size = 1024 * 1024  # 1MB
    chunks = []
    total_size = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file exceeds maximum permissible size limit of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    validate_file_size(len(content))
    verified_mime = validate_magic_bytes(content, file.filename)

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 2. Resolve document type if specified (400 if unknown)
    KNOWN_SYSTEM_DOC_TYPES = {"emirates_id", "uae_trade_license", "commercial_invoice"}
    doc_type_id = None
    if document_type_code:
        stmt = select(DocumentType).where(
            and_(
                DocumentType.tenant_id == actor.tenant_id,
                DocumentType.code == document_type_code
            )
        )
        res = await db.execute(stmt)
        dt = res.scalar_one_or_none()
        if not dt:
            if document_type_code not in KNOWN_SYSTEM_DOC_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown document_type_code '{document_type_code}' for this tenant"
                )
            dt = DocumentType(
                tenant_id=actor.tenant_id,
                code=document_type_code,
                name_en=document_type_code.replace("_", " ").title(),
                name_ar=document_type_code,
                schema_definition={}
            )
            db.add(dt)
            await db.flush()
        doc_type_id = dt.id

    # 3. Create document record and upload to S3/local sovereign store
    from app.models.base import generate_uuid
    doc_id = generate_uuid()
    raw_filename = file.filename or f"upload_{doc_id}"
    cleaned_basename = os.path.basename(raw_filename.replace("\\", "/"))
    if not cleaned_basename or cleaned_basename in [".", ".."]:
        cleaned_basename = f"upload_{doc_id}"

    storage_path = storage_service.upload_document_file(
        tenant_id=actor.tenant_id,
        document_id=doc_id,
        filename=cleaned_basename,
        content=content,
        mime_type=verified_mime
    )

    new_doc = Document(
        id=doc_id,
        tenant_id=actor.tenant_id,
        document_type_id=doc_type_id,
        file_name=cleaned_basename,
        file_size=len(content),
        mime_type=verified_mime,
        storage_path=storage_path,
        status="queued",
        uploaded_by=actor.id
    )
    db.add(new_doc)
    await db.flush()

    # 4. Record immutable audit log
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_UPLOAD",
        entity_type="document",
        entity_id=doc_id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "file_name": cleaned_basename,
            "file_size": len(content),
            "mime_type": verified_mime,
            "document_type_code": document_type_code,
            "storage_path": storage_path
        }
    )
    await db.commit()
    await db.refresh(new_doc)

    # 5. Enqueue background extraction pipeline
    from app.worker.queue import enqueue_document_job
    enqueue_document_job(doc_id, actor.tenant_id)

    # Emit real-time queued event
    from app.services.event_bus import event_bus
    await event_bus.emit_event(
        tenant_id=actor.tenant_id,
        document_id=doc_id,
        stage="queued",
        status="queued",
        progress_pct=5,
        details={"file_name": cleaned_basename, "file_size": len(content)}
    )

    return DocumentResponse(
        id=new_doc.id,
        tenant_id=new_doc.tenant_id,
        document_type_id=new_doc.document_type_id,
        document_type_code=document_type_code,
        file_name=new_doc.file_name,
        file_size=new_doc.file_size,
        mime_type=new_doc.mime_type,
        status=new_doc.status,
        confidence_score=new_doc.confidence_score,
        language_detected=new_doc.language_detected,
        created_at=new_doc.created_at,
        updated_at=new_doc.updated_at
    )

@router.get("", response_model=DocumentListResponse, include_in_schema=False)
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None),
    document_type_code: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """Lists documents with query-level tenant isolation and filtering."""
    conditions = [Document.tenant_id == actor.tenant_id]

    if status:
        conditions.append(Document.status == status)
    if from_date:
        conditions.append(Document.created_at >= from_date)
    if to_date:
        conditions.append(Document.created_at <= to_date)
    if document_type_code:
        dt_stmt = select(DocumentType.id).where(
            and_(DocumentType.tenant_id == actor.tenant_id, DocumentType.code == document_type_code)
        )
        dt_res = await db.execute(dt_stmt)
        dt_id = dt_res.scalar_one_or_none()
        if dt_id:
            conditions.append(Document.document_type_id == dt_id)
        else:
            return DocumentListResponse(total=0, documents=[])

    # Count total
    count_stmt = select(func.count(Document.id)).where(and_(*conditions))
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Query page with document_type_code
    stmt = (
        select(Document, DocumentType.code)
        .outerjoin(DocumentType, Document.document_type_id == DocumentType.id)
        .where(and_(*conditions))
        .order_by(desc(Document.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    rows = res.all()

    return DocumentListResponse(
        total=total,
        documents=[
            DocumentResponse(
                id=d.id,
                tenant_id=d.tenant_id,
                document_type_id=d.document_type_id,
                document_type_code=code,
                file_name=d.file_name,
                file_size=d.file_size,
                mime_type=d.mime_type,
                status=d.status,
                confidence_score=d.confidence_score,
                language_detected=d.language_detected,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
            for d, code in rows
        ]
    )

# Place /events routes BEFORE /{id} routes to prevent router shadowing
@router.get("/events/stream")
@router.get("/events")
async def stream_tenant_events(
    request: Request,
    actor: AuthenticatedActor = Depends(require_stream_permission(Permission.DOCUMENT_VIEW)),
):
    """
    Server-Sent Events (SSE) stream for all pipeline events belonging to the current tenant.
    Enforces strict tenant isolation: users never receive another tenant's events.
    """
    import asyncio
    from app.services.event_bus import event_bus

    async def event_generator():
        yield ": connected\n\n"
        try:
            async for evt in event_bus.subscribe_tenant(actor.tenant_id):
                if await request.is_disconnected():
                    break
                data = json.dumps(evt, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/{id}", response_model=DocumentDetailResponse)
async def get_document(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves document details, extracted fields, pages, and validation errors."""
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Fetch child relationships
    fields_res = await db.execute(
        select(ExtractedField).where(and_(ExtractedField.document_id == id, ExtractedField.tenant_id == actor.tenant_id))
    )
    fields = fields_res.scalars().all()

    pages_res = await db.execute(
        select(DocumentPage).where(and_(DocumentPage.document_id == id, DocumentPage.tenant_id == actor.tenant_id))
    )
    pages = pages_res.scalars().all()

    val_res = await db.execute(
        select(ValidationResult).where(and_(ValidationResult.document_id == id, ValidationResult.tenant_id == actor.tenant_id))
    )
    validations = val_res.scalars().all()

    # Log audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_VIEW",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    await db.commit()

    # Resolve document_type_code
    doc_type_code = None
    if doc.document_type_id:
        dt_res = await db.execute(select(DocumentType.code).where(DocumentType.id == doc.document_type_id))
        doc_type_code = dt_res.scalar_one_or_none()

    # Determine PII masking by actor role and tenant preference
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == actor.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_pii_default = tenant.pii_masking_default if tenant is not None else True

    should_mask = False
    if actor.role in ("viewer", "api_client"):
        should_mask = True
    elif tenant_pii_default and actor.role not in ("admin", "reviewer"):
        should_mask = True

    response_fields = []
    for f in fields:
        f_val = f.value
        f_raw = f.raw_value
        f_corr = f.corrected_value
        if should_mask:
            f_val = mask_pii_value(f.field_name, f.value) if f.value else f.value
            f_raw = mask_pii_value(f.field_name, f.raw_value) if f.raw_value else f.raw_value
            f_corr = mask_pii_value(f.field_name, f.corrected_value) if f.corrected_value else f.corrected_value
        response_fields.append(
            ExtractedFieldResponse(
                id=f.id,
                field_name=f.field_name,
                value=f_val,
                raw_value=f_raw,
                confidence=f.confidence,
                page_number=f.page_number,
                bounding_box=f.bounding_box,
                is_corrected=f.is_corrected,
                corrected_value=f_corr,
                corrected_at=f.corrected_at
            )
        )

    return DocumentDetailResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        document_type_id=doc.document_type_id,
        document_type_code=doc_type_code,
        file_name=doc.file_name,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status,
        confidence_score=doc.confidence_score,
        language_detected=doc.language_detected,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        extracted_fields=response_fields,
        pages=pages,
        validation_results=validations
    )

@router.get("/{id}/file")
async def get_document_file(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """Streams original document binary with tamper-proof audit logging."""
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = storage_service.get_document_bytes(doc.storage_path)

    # Log file download audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_VIEW",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"stream_binary": True, "file_name": doc.file_name, "size": len(content)}
    )
    await db.commit()

    import urllib.parse
    ascii_filename = re.sub(r"[^\x20-\x7E]", "_", doc.file_name)
    encoded_filename = urllib.parse.quote(doc.file_name, encoding="utf-8")
    content_disposition = f'inline; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'

    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={"Content-Disposition": content_disposition}
    )

@router.delete("/{id}")
async def delete_document(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_DELETE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Hard-deletes document file from S3 storage and deletes all derived data
    (extracted fields, validation results, pages). Keeps only an immutable audit record.
    Enforces admin RBAC and tenant isolation.
    """
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_name = doc.file_name
    storage_path = doc.storage_path

    # 1. Hard-delete binary files from storage
    storage_service.delete_document_artifacts(
        tenant_id=actor.tenant_id,
        document_id=id,
        storage_path=storage_path
    )

    # 2. Hard delete database record and all derived data (chunks, fields, validations, pages)
    from app.models.document import DocumentPage, ExtractedField, ValidationResult
    from app.models.document_chunk import DocumentChunk
    from sqlalchemy import delete

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == id))
    await db.execute(delete(ExtractedField).where(ExtractedField.document_id == id))
    await db.execute(delete(ValidationResult).where(ValidationResult.document_id == id))
    await db.execute(delete(DocumentPage).where(DocumentPage.document_id == id))
    await db.delete(doc)

    # 3. Log immutable audit trail
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_DELETE",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "file_name": file_name,
            "storage_path": storage_path,
            "hard_deleted": True
        }
    )
    await db.commit()

    return {"status": "deleted", "id": id, "file_name": file_name}

@router.post("/retention/sweep")
async def trigger_retention_sweep(
    actor: AuthenticatedActor = Depends(require_permission(Permission.RETENTION_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers the tenant retention policy sweep (purging caller's tenant only)."""
    result = await run_retention_policy_sweep(db, tenant_id=actor.tenant_id)
    return result

@router.patch("/{id}/fields/{field_name}", response_model=ExtractedFieldResponse)
async def correct_document_field(
    id: str,
    field_name: str,
    payload: FieldCorrectionRequest,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_REVIEW)),
    db: AsyncSession = Depends(get_db)
):
    """
    Reviewer field correction endpoint.
    Status rule: correct only from needs_review; else 409.
    Correction uses the document's real type and recalculates confidence.
    """
    doc_stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    doc_res = await db.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status != "needs_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot correct field: document status is '{doc.status}'. Corrections are only permitted from 'needs_review'."
        )

    stmt = select(ExtractedField).where(
        and_(
            ExtractedField.document_id == id,
            ExtractedField.field_name == field_name,
            ExtractedField.tenant_id == actor.tenant_id
        )
    )
    res = await db.execute(stmt)
    field = res.scalar_one_or_none()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field '{field_name}' not found on document {id}"
        )

    original_val = field.value
    field.is_corrected = True
    field.corrected_value = payload.corrected_value
    field.value = payload.corrected_value
    field.corrected_by = actor.id
    field.corrected_at = datetime.now(timezone.utc)
    field.confidence = 1.0  # Human reviewer verified

    # Re-evaluate validation rules for this document
    all_fields_res = await db.execute(
        select(ExtractedField).where(
            and_(ExtractedField.document_id == id, ExtractedField.tenant_id == actor.tenant_id)
        )
    )
    all_fields = all_fields_res.scalars().all()

    from app.services.model_engine.base import ExtractedFieldData
    from app.pipeline.validator import run_validation_rules
    field_data_list = [
        ExtractedFieldData(
            field_name=f.field_name,
            value=f.value,
            raw_value=f.raw_value or "",
            confidence=f.confidence,
            page_number=f.page_number
        )
        for f in all_fields
    ]

    # Resolve document's real type (do NOT default unknown documents to emirates_id)
    doc_type_code = "unknown"
    schema_def = {}
    if doc.document_type_id:
        dt_res = await db.execute(select(DocumentType).where(DocumentType.id == doc.document_type_id))
        dt = dt_res.scalar_one_or_none()
        if dt:
            doc_type_code = dt.code
            schema_def = dt.schema_definition or {}

    val_outcomes = run_validation_rules(doc_type_code, field_data_list, schema_def)

    # Recalculate document overall confidence
    all_found = [f for f in all_fields if f.value is not None]
    doc.confidence_score = round(sum(f.confidence for f in all_found) / len(all_found), 2) if all_found else 0.0

    # Delete old and insert new validations
    from sqlalchemy import delete
    await db.execute(
        delete(ValidationResult).where(
            and_(ValidationResult.document_id == id, ValidationResult.tenant_id == actor.tenant_id)
        )
    )
    for vo in val_outcomes:
        db.add(ValidationResult(
            document_id=id,
            tenant_id=actor.tenant_id,
            rule_name=vo["rule_name"],
            passed=vo["passed"],
            severity=vo["severity"],
            message=vo["message"]
        ))

    # Log immutable audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="FIELD_CORRECT",
        entity_type="extracted_field",
        entity_id=field.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "document_id": id,
            "field_name": field_name,
            "original_value": original_val,
            "corrected_value": payload.corrected_value,
            "reason": payload.reason,
            "recalculated_confidence": doc.confidence_score
        }
    )
    await db.commit()
    await db.refresh(field)

    return field

@router.post("/{id}/approve")
async def approve_document(
    id: str,
    request: Request,
    force: bool = Query(False),
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_APPROVE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Approves document.
    Status rules: approve only from needs_review/approved and not with failed error validations
    (unless admin force=true, audited); else 409.
    """
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status not in ("needs_review", "approved"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve document with status '{doc.status}'. Approvals only permitted from 'needs_review' or 'approved'."
        )

    # Check for failed error validations
    val_stmt = select(ValidationResult).where(
        and_(
            ValidationResult.document_id == id,
            ValidationResult.tenant_id == actor.tenant_id,
            ValidationResult.passed == False,
            ValidationResult.severity == "error"
        )
    )
    failed_errors = (await db.execute(val_stmt)).scalars().all()
    if failed_errors and not (force and actor.role == "admin"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve document with {len(failed_errors)} failed error validations without admin force=true."
        )

    is_forced = bool(failed_errors and force and actor.role == "admin")
    doc.status = "approved"

    # Fetch extracted fields for webhook payload
    fields_res = await db.execute(
        select(ExtractedField).where(
            and_(ExtractedField.document_id == id, ExtractedField.tenant_id == actor.tenant_id)
        )
    )
    fields = fields_res.scalars().all()
    fields_dict = {f.field_name: f.value for f in fields}

    # Dispatch signed webhook
    from app.services.webhook_service import dispatch_document_approved_webhook
    webhook_meta = await dispatch_document_approved_webhook(
        tenant_id=actor.tenant_id,
        document_id=id,
        document_data={
            "file_name": doc.file_name,
            "status": "approved",
            "confidence_score": doc.confidence_score,
            "fields": fields_dict
        }
    )

    # Log audit event
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_APPROVE_FORCED" if is_forced else "DOCUMENT_APPROVE",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "file_name": doc.file_name,
            "force_override": is_forced,
            "failed_validations_count": len(failed_errors),
            "webhook_dispatched": webhook_meta.get("dispatched"),
            "webhook_signature": webhook_meta.get("signature")
        }
    )
    await db.commit()

    return {
        "status": "approved",
        "document_id": id,
        "force_override": is_forced,
        "webhook": {
            "dispatched": webhook_meta.get("dispatched", False),
            "reason": webhook_meta.get("reason", "no_webhook_endpoint_configured"),
            "signature": webhook_meta.get("signature"),
            "timestamp": webhook_meta.get("timestamp")
        }
    }

@router.post("/{id}/reject")
async def reject_document(
    id: str,
    payload: RejectDocumentRequest,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_APPROVE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Rejects document with reason and immutable audit log.
    Status rule: reject from needs_review/approved; else 409.
    """
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status not in ("needs_review", "approved"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject document with status '{doc.status}'. Rejections only permitted from 'needs_review' or 'approved'."
        )

    doc.status = "rejected"

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_REJECT",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "file_name": doc.file_name,
            "rejection_reason": payload.rejection_reason
        }
    )
    await db.commit()

    return {
        "status": "rejected",
        "document_id": id,
        "rejection_reason": payload.rejection_reason
    }

@router.get("/{id}/export")
async def export_document_data(
    id: str,
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    mask_pii: Optional[bool] = Query(None),
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_EXPORT)),
    db: AsyncSession = Depends(get_db)
):
    """
    Exports extracted structured data as JSON or CSV.
    Supports PII masking option for Emirates ID and confidential data compliance.
    """
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    fields_res = await db.execute(
        select(ExtractedField).where(
            and_(ExtractedField.document_id == id, ExtractedField.tenant_id == actor.tenant_id)
        )
    )
    fields = fields_res.scalars().all()

    # Determine PII masking: default to tenant pii_masking_default, only admin may unmask
    stmt_tenant = select(Tenant).where(Tenant.id == actor.tenant_id)
    res_tenant = await db.execute(stmt_tenant)
    tenant = res_tenant.scalar_one_or_none()
    default_mask = tenant.pii_masking_default if tenant is not None else True

    if mask_pii is None:
        should_mask = default_mask
    else:
        if mask_pii is False:
            if actor.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Only administrators may unmask PII during export"
                )
            should_mask = False
        else:
            should_mask = True

    from app.core.security import mask_pii_value

    export_data = {}
    for f in fields:
        raw_val = f.value
        val = mask_pii_value(f.field_name, raw_val) if should_mask else raw_val
        export_data[f.field_name] = {
            "value": val,
            "confidence": f.confidence,
            "is_corrected": f.is_corrected,
            "page_number": f.page_number
        }

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # If unmasked, audit PII_UNMASKED
    if not should_mask:
        await log_audit_event(
            db=db,
            tenant_id=actor.tenant_id,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role,
            action="PII_UNMASKED",
            entity_type="document",
            entity_id=id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"format": format, "reason": "unmasked export"}
        )

    # Log export audit event
    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_EXPORT",
        entity_type="document",
        entity_id=id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"format": format, "mask_pii": should_mask}
    )
    await db.commit()

    if format == "csv":
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field_name", "value", "confidence", "is_corrected", "page_number"])
        for k, v in export_data.items():
            writer.writerow([k, v["value"], v["confidence"], v["is_corrected"], v["page_number"]])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="document_{id}_export.csv"'}
        )

    import json
    return Response(
        content=json.dumps({
            "document_id": doc.id,
            "file_name": doc.file_name,
            "status": doc.status,
            "confidence_score": doc.confidence_score,
            "pii_masked": should_mask,
            "fields": export_data
        }, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="document_{id}_export.json"'}
    )


@router.get("/{id}/events")
async def stream_document_events(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_stream_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """
    Server-Sent Events (SSE) stream for a specific document.
    Enforces tenant isolation: rejects requests if document belongs to another tenant.
    """
    stmt = select(Document).where(and_(Document.id == id, Document.tenant_id == actor.tenant_id))
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    import asyncio
    from app.services.event_bus import event_bus

    async def event_generator():
        yield ": connected\n\n"
        try:
            async for evt in event_bus.subscribe_document(actor.tenant_id, id):
                if await request.is_disconnected():
                    break
                data = json.dumps(evt, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
