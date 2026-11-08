from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rbac import Permission
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.user import UserCreate
from app.services.audit_service import log_audit_event
from app.api.deps import require_permission, AuthenticatedActor

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post("/onboard", response_model=TenantResponse)
async def onboard_tenant(
    payload: TenantCreate,
    admin_user: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Initial tenant setup endpoint creating the tenant and primary administrator."""
    # Check if slug exists
    stmt = select(Tenant).where(Tenant.slug == payload.slug)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tenant with this slug already exists")

    # Check if admin email exists
    stmt_user = select(User).where(User.email == admin_user.email)
    res_user = await db.execute(stmt_user)
    if res_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        tier=payload.tier,
        retention_days=payload.retention_days,
        pii_masking_default=payload.pii_masking_default,
    )
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=admin_user.email,
        hashed_password=hash_password(admin_user.password),
        full_name=admin_user.full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=tenant.id,
        actor_id=user.id,
        actor_email=user.email,
        actor_role="admin",
        action="TENANT_ONBOARDED",
        entity_type="tenant",
        entity_id=tenant.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"tenant_name": tenant.name, "slug": tenant.slug}
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.get("/me", response_model=TenantResponse)
async def get_current_tenant_info(
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, actor.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.patch("/me", response_model=TenantResponse)
async def update_current_tenant_settings(
    payload: TenantUpdate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.TENANT_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, actor.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    diff = {}
    if payload.name is not None and payload.name != tenant.name:
        diff["name"] = {"old": tenant.name, "new": payload.name}
        tenant.name = payload.name
    if payload.tier is not None and payload.tier != tenant.tier:
        diff["tier"] = {"old": tenant.tier, "new": payload.tier}
        tenant.tier = payload.tier
    if payload.retention_days is not None and payload.retention_days != tenant.retention_days:
        diff["retention_days"] = {"old": tenant.retention_days, "new": payload.retention_days}
        tenant.retention_days = payload.retention_days
    if payload.pii_masking_default is not None and payload.pii_masking_default != tenant.pii_masking_default:
        diff["pii_masking_default"] = {"old": tenant.pii_masking_default, "new": payload.pii_masking_default}
        tenant.pii_masking_default = payload.pii_masking_default

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="TENANT_SETTINGS_UPDATED",
        entity_type="tenant",
        entity_id=tenant.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details=diff
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant
