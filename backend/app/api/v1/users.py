from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rbac import Permission, UserRole
from app.core.security import hash_password, generate_api_key
from app.models.user import User, ApiKey
from app.schemas.user import UserCreate, UserResponse, ApiKeyCreate, ApiKeyResponse
from app.services.audit_service import log_audit_event
from app.api.deps import require_permission, AuthenticatedActor

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("", response_model=List[UserResponse], include_in_schema=False)
@router.get("/", response_model=List[UserResponse])
async def list_users(
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """List users belonging strictly to the authenticated actor's tenant."""
    stmt = select(User).where(User.tenant_id == actor.tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=UserResponse)
async def create_user(
    payload: UserCreate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Admin adds a new user to their tenant."""
    # Check if email is already in use
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        tenant_id=actor.tenant_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.value if isinstance(payload.role, UserRole) else str(payload.role),
        is_active=True
    )
    db.add(new_user)
    await db.flush()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_CREATED",
        entity_type="user",
        entity_id=new_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"created_user_email": new_user.email, "role": new_user.role}
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_tenant_api_key(
    payload: ApiKeyCreate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Generates a secure API key for integration with external UAE banking/enterprise systems."""
    raw_key, key_hash, prefix = generate_api_key(actor.tenant_id)
    
    api_key_obj = ApiKey(
        tenant_id=actor.tenant_id,
        name=payload.name,
        prefix=prefix,
        key_hash=key_hash,
        role=payload.role.value if isinstance(payload.role, UserRole) else str(payload.role),
        is_active=True
    )
    db.add(api_key_obj)
    await db.flush()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="API_KEY_CREATED",
        entity_type="api_key",
        entity_id=api_key_obj.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"key_name": payload.name, "prefix": prefix}
    )
    await db.commit()
    await db.refresh(api_key_obj)
    
    response = ApiKeyResponse.model_validate(api_key_obj)
    response.raw_key = raw_key
    return response
