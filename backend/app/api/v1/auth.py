from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
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
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 1. Check brute-force rate limit & temporary lockout status
    login_rate_limiter.check_lockout(client_ip, payload.email)

    stmt = select(User).where(User.email == payload.email, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Record failed attempt in rate limiter
        newly_locked = login_rate_limiter.record_failure(client_ip, payload.email)

        action = "AUTH_LOGIN_LOCKED_OUT" if newly_locked else "AUTH_LOGIN_FAILED"
        tenant_id = user.tenant_id if user else settings.DEFAULT_TENANT_ID
        actor_id = user.id if user else "unregistered_or_invalid"
        actor_email = user.email if user else payload.email
        actor_role = user.role if user else "anonymous"

        await log_audit_event(
            db=db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            entity_type="user",
            entity_id=actor_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "reason": "invalid_credentials",
                "locked_out": newly_locked,
                "lockout_minutes": settings.LOGIN_LOCKOUT_MINUTES if newly_locked else 0
            }
        )
        await db.commit()

        if newly_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Security lockout: Maximum failed login attempts exceeded. "
                    f"Account/IP locked for {settings.LOGIN_LOCKOUT_MINUTES} minutes."
                ),
                headers={"Retry-After": str(settings.LOGIN_LOCKOUT_MINUTES * 60)}
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check tenant active
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant account is disabled")

    # Success: clear failed attempts tracker
    login_rate_limiter.record_success(client_ip, payload.email)

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
        "tenant_id": actor.tenant_id,
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.tier,
            "retention_days": tenant.retention_days,
            "pii_masking_default": tenant.pii_masking_default
        } if tenant else None,
        "full_name": user.full_name if user else "API Client"
    }
