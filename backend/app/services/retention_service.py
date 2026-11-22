import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.tenant import Tenant
from app.models.document import Document
from app.services.storage_service import storage_service
from app.services.audit_service import log_audit_event

logger = logging.getLogger("retention_service")

async def run_retention_policy_sweep(db: AsyncSession, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Scheduled retention policy job.
    Identifies documents exceeding tenant retention_days and permanently hard-deletes
    all derived data and stored binaries, leaving only an immutable audit record.
    When tenant_id is specified, operates strictly on that single tenant.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Tenant).where(Tenant.is_active == True)
    if tenant_id:
        stmt = stmt.where(Tenant.id == tenant_id)
    tenants_res = await db.execute(stmt)
    tenants = tenants_res.scalars().all()

    total_purged = 0
    purged_by_tenant = {}

    for tenant in tenants:
        retention_days = tenant.retention_days or 365
        cutoff_date = now - timedelta(days=retention_days)

        # Select documents older than cutoff
        stmt = select(Document).where(
            and_(
                Document.tenant_id == tenant.id,
                Document.created_at < cutoff_date
            )
        )
        docs_res = await db.execute(stmt)
        expired_docs = docs_res.scalars().all()

        purged_count = 0
        for doc in expired_docs:
            doc_id = doc.id
            file_name = doc.file_name

            # 1. Hard delete from S3/local storage
            storage_service.delete_document_artifacts(
                tenant_id=tenant.id,
                document_id=doc_id,
                storage_path=doc.storage_path
            )

            # 2. Hard delete document and all cascade derived data from DB
            from app.models.document import DocumentPage, ExtractedField, ValidationResult
            from app.models.document_chunk import DocumentChunk
            from sqlalchemy import delete

            await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
            await db.execute(delete(ExtractedField).where(ExtractedField.document_id == doc_id))
            await db.execute(delete(ValidationResult).where(ValidationResult.document_id == doc_id))
            await db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc_id))
            await db.delete(doc)

            # 3. Log immutable audit trail
            await log_audit_event(
                db=db,
                tenant_id=tenant.id,
                actor_id="system_retention_job",
                actor_email="system@retention.local",
                actor_role="system",
                action="RETENTION_EXPIRY_PURGE",
                entity_type="document",
                entity_id=doc_id,
                details={
                    "file_name": file_name,
                    "retention_days": retention_days,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "purged_at": now.isoformat()
                }
            )
            purged_count += 1

        if purged_count > 0:
            await db.commit()
            logger.info(f"Tenant {tenant.id} retention sweep: purged {purged_count} documents.")

        purged_by_tenant[tenant.id] = purged_count
        total_purged += purged_count

    return {
        "status": "completed",
        "total_purged": total_purged,
        "tenants_swept": len(tenants),
        "details": purged_by_tenant,
        "swept_at": now.isoformat()
    }
