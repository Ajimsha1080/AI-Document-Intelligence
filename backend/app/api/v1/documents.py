from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.core.config import settings
from app.core.file_validator import validate_magic_bytes, validate_file_size
from app.api.deps import get_current_actor, require_role, AuthenticatedActor
from app.models.document import Document, DocumentPage, ExtractedField, ValidationResult
from app.models.document_type import DocumentType
from app.schemas.document import DocumentResponse, DocumentDetailResponse, DocumentListResponse
from app.services.storage_service import storage_service
from app.services.audit_service import log_audit_event
from app.services.retention_service import run_retention_policy_sweep

router = APIRouter(prefix="/documents", tags=["Documents Management"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type_code: Optional[str] = Form(None),
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests and stores business documents into sovereign S3 storage.
    Validates file content by magic bytes (PDF, JPG, PNG, TIFF) and size ceiling.
    Enforces tenant isolation and records immutable audit event.
    """
    # 1. Read and validate content
    content = await file.read()
    validate_file_size(len(content))
    verified_mime = validate_magic_bytes(content)

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 2. Resolve document type if specified
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
        if dt:
            doc_type_id = dt.id

    # 3. Create document record and upload to S3/local sovereign store
    from app.models.base import generate_uuid
    doc_id = generate_uuid()
    safe_filename = file.filename or f"upload_{doc_id}"

    storage_path = storage_service.upload_document_file(
        tenant_id=actor.tenant_id,
        document_id=doc_id,
        filename=safe_filename,
        content=content,
        mime_type=verified_mime
    )

    new_doc = Document(
        id=doc_id,
        tenant_id=actor.tenant_id,
        document_type_id=doc_type_id,
        file_name=safe_filename,
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
            "file_name": safe_filename,
            "file_size": len(content),
            "mime_type": verified_mime,
            "document_type_code": document_type_code,
            "storage_path": storage_path
        }
    )
    await db.commit()
    await db.refresh(new_doc)

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

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None),
    document_type_code: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: AuthenticatedActor = Depends(get_current_actor),
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

    # Query page
    stmt = (
        select(Document)
        .where(and_(*conditions))
        .order_by(desc(Document.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    return DocumentListResponse(
        total=total,
        documents=[
            DocumentResponse(
                id=d.id,
                tenant_id=d.tenant_id,
                document_type_id=d.document_type_id,
                file_name=d.file_name,
                file_size=d.file_size,
                mime_type=d.mime_type,
                status=d.status,
                confidence_score=d.confidence_score,
                language_detected=d.language_detected,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
            for d in docs
        ]
    )

@router.get("/{id}", response_model=DocumentDetailResponse)
async def get_document(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(get_current_actor),
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

    return DocumentDetailResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        document_type_id=doc.document_type_id,
        file_name=doc.file_name,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status,
        confidence_score=doc.confidence_score,
        language_detected=doc.language_detected,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        extracted_fields=fields,
        pages=pages,
        validation_results=validations
    )

@router.get("/{id}/file")
async def get_document_file(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(get_current_actor),
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

    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'}
    )

@router.delete("/{id}")
async def delete_document(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_role("admin")),
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

    # 2. Delete database record (cascades to pages, extracted_fields, validation_results)
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
    actor: AuthenticatedActor = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers the tenant retention policy sweep (Admin only)."""
    result = await run_retention_policy_sweep(db)
    return result
