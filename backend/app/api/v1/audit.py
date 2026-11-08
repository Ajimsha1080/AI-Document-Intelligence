from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.rbac import Permission
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse
from app.api.deps import require_permission, AuthenticatedActor

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by audit action"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: AuthenticatedActor = Depends(require_permission(Permission.AUDIT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """
    Query immutable audit logs for the current tenant.
    Enforces strict multi-tenant boundary: only logs belonging to actor's tenant are visible.
    """
    stmt = select(AuditLog).where(AuditLog.tenant_id == actor.tenant_id)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)

    stmt = stmt.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
