import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.services.audit_service import log_audit_event

logger = logging.getLogger("stuck_job_sweeper")

async def sweep_stuck_jobs(db: AsyncSession, timeout_seconds: int = 300) -> int:
    """
    Finds documents stuck in 'processing' state past timeout_seconds (default 5 mins),
    and transitions them to 'failed' with visible error messages and audit logs.
    No job can remain stuck forever.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=timeout_seconds)

    stmt = select(Document).where(
        and_(
            Document.status == "processing",
            Document.updated_at < cutoff
        )
    )
    res = await db.execute(stmt)
    stuck_docs = res.scalars().all()

    swept_count = 0
    for doc in stuck_docs:
        doc.status = "failed"
        await log_audit_event(
            db=db,
            tenant_id=doc.tenant_id,
            actor_id="system_sweeper",
            actor_email="sweeper@pipeline.local",
            actor_role="system",
            action="DOCUMENT_PROCESS_TIMEOUT",
            entity_type="document",
            entity_id=doc.id,
            details={
                "timeout_seconds": timeout_seconds,
                "message": f"Job timed out after {timeout_seconds}s in processing state. Marked failed by sweeper."
            }
        )
        swept_count += 1

    if swept_count > 0:
        await db.commit()
        logger.warning(f"Stuck job sweeper: marked {swept_count} stuck jobs as failed.")

    return swept_count
