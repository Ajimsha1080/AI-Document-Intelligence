import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.document import Document
from app.services.audit_service import log_audit_event
from app.services.event_bus import event_bus

logger = logging.getLogger("stuck_job_sweeper")

async def sweep_stuck_jobs(db: AsyncSession, timeout_seconds: int = 300, queued_timeout_minutes: int = 15) -> int:
    """
    Finds documents stuck in:
    1. 'processing' state past timeout_seconds (default 5 mins), OR
    2. 'queued' state past queued_timeout_minutes (default 15 mins).
    Transitions them to 'failed', records immutable audit logs, and emits failure events.
    """
    now = datetime.now(timezone.utc)
    processing_cutoff = now - timedelta(seconds=timeout_seconds)
    queued_cutoff = now - timedelta(minutes=queued_timeout_minutes)

    stmt = select(Document).where(
        or_(
            and_(Document.status == "processing", Document.updated_at < processing_cutoff),
            and_(Document.status == "queued", Document.created_at < queued_cutoff)
        )
    )
    res = await db.execute(stmt)
    stuck_docs = res.scalars().all()

    swept_count = 0
    for doc in stuck_docs:
        prev_status = doc.status
        doc.status = "failed"
        reason = f"Job timed out after exceeding limit in '{prev_status}' state. Marked failed by sweeper."

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
                "previous_status": prev_status,
                "timeout_seconds": timeout_seconds if prev_status == "processing" else queued_timeout_minutes * 60,
                "message": reason
            }
        )

        try:
            await event_bus.emit_event(
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                stage="failed",
                status="failed",
                progress_pct=100,
                details={"error": reason}
            )
        except Exception:
            pass

        swept_count += 1

    if swept_count > 0:
        await db.commit()
        logger.warning(f"Stuck job sweeper: marked {swept_count} stuck jobs as failed.")

    return swept_count
