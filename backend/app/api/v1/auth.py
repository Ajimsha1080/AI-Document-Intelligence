from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.auth import LoginRequest, Token
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_actor, AuthenticatedActor

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == payload.email, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    if not user or not verify_password(payload.password, user.hashed_password):
        # Log failed attempt
        if user:
            await log_audit_event(
                db=db,
                tenant_id=user.tenant_id,
                actor_id=user.id,
                actor_email=user.email,
                actor_role=user.role,
                action="AUTH_LOGIN_FAILED",
                entity_type="user",
                entity_id=user.id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"reason": "invalid_credentials"}
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check tenant active
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant account is disabled")

    # Generate token
    token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role
    )

    # Audit login success
    await log_audit_event(
        db=db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    await db.commit()

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        full_name=user.full_name
    )

@router.get("/me")
async def get_me(
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, actor.tenant_id)
    user = await db.get(User, actor.id) if not actor.is_api_client else None
    return {
        "id": actor.id,
        "email": actor.email,
        "role": actor.role,
        "is_api_client": actor.is_api_client,
        "full_name": user.full_name if user else "API Key Client",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.tier,
            "retention_days": tenant.retention_days,
            "pii_masking_default": tenant.pii_masking_default
        }
    }
