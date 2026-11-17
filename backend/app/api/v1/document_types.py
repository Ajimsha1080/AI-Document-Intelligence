from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rbac import Permission
from app.models.document_type import DocumentType
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeResponse,
    DEFAULT_EMIRATES_ID_SCHEMA,
    DEFAULT_TRADE_LICENSE_SCHEMA
)
from app.services.audit_service import log_audit_event
from app.api.deps import require_permission, AuthenticatedActor

router = APIRouter(prefix="/document-types", tags=["Document Types"])

@router.get("", response_model=List[DocumentTypeResponse], include_in_schema=False)
@router.get("/", response_model=List[DocumentTypeResponse])
async def list_document_types(
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all document types configured for the current tenant."""
    stmt = select(DocumentType).where(
        DocumentType.tenant_id == actor.tenant_id,
        DocumentType.is_active == True
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=DocumentTypeResponse)
async def create_document_type(
    payload: DocumentTypeCreate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.SCHEMA_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Admin creates or registers a new configurable document type schema."""
    # Check duplicate code within tenant
    stmt = select(DocumentType).where(
        DocumentType.tenant_id == actor.tenant_id,
        DocumentType.code == payload.code
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Document type '{payload.code}' already exists for this tenant")

    doc_type = DocumentType(
        tenant_id=actor.tenant_id,
        code=payload.code,
        name_en=payload.name_en,
        name_ar=payload.name_ar,
        description=payload.description,
        schema_definition=payload.schema_definition.model_dump(),
        is_active=True
    )
    db.add(doc_type)
    await db.flush()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="DOCUMENT_TYPE_CREATED",
        entity_type="document_type",
        entity_id=doc_type.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"code": doc_type.code, "name_en": doc_type.name_en}
    )
    await db.commit()
    await db.refresh(doc_type)
    return doc_type

@router.post("/seed-defaults", response_model=List[DocumentTypeResponse])
async def seed_standard_uae_document_types(
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.SCHEMA_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Seeds standard UAE Emirates ID and UAE Trade License schemas for the tenant."""
    created = []
    
    defaults = [
        {
            "code": "emirates_id",
            "name_en": "UAE Identity Card (Emirates ID)",
            "name_ar": "بطاقة الهوية الإماراتية",
            "description": "Federal Authority for Identity and Citizenship (ICP) National ID card",
            "schema_definition": DEFAULT_EMIRATES_ID_SCHEMA.model_dump()
        },
        {
            "code": "uae_trade_license",
            "name_en": "UAE Commercial Trade License",
            "name_ar": "رخصة تجارية في دولة الإمارات",
            "description": "Department of Economy and Tourism (DET / DED / Freezones) commercial license",
            "schema_definition": DEFAULT_TRADE_LICENSE_SCHEMA.model_dump()
        }
    ]

    for item in defaults:
        stmt = select(DocumentType).where(
            DocumentType.tenant_id == actor.tenant_id,
            DocumentType.code == item["code"]
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if not existing:
            dt = DocumentType(
                tenant_id=actor.tenant_id,
                code=item["code"],
                name_en=item["name_en"],
                name_ar=item["name_ar"],
                description=item["description"],
                schema_definition=item["schema_definition"],
                is_active=True
            )
            db.add(dt)
            created.append(dt)

    if created:
        await db.flush()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        await log_audit_event(
            db=db,
            tenant_id=actor.tenant_id,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role,
            action="SCHEMAS_DEFAULT_SEEDED",
            entity_type="document_type",
            entity_id=actor.tenant_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"seeded_codes": [d.code for d in created]}
        )
        await db.commit()
        for d in created:
            await db.refresh(d)

    # Return all tenant document types
    stmt = select(DocumentType).where(
        DocumentType.tenant_id == actor.tenant_id,
        DocumentType.is_active == True
    )
    all_res = await db.execute(stmt)
    return all_res.scalars().all()
