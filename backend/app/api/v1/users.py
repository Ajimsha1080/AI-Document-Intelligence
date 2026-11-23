from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.rbac import Permission, UserRole
from app.core.security import hash_password, generate_api_key
from app.models.user import User, ApiKey
from app.schemas.user import UserCreate, UserUpdate, UserResponse, ApiKeyCreate, ApiKeyResponse
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
    clean_email = payload.email.strip().lower()
    # Check if email is already in use
    stmt = select(User).where(User.email == clean_email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        tenant_id=actor.tenant_id,
        email=clean_email,
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

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_tenant_api_keys(
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Lists API keys issued for the caller's tenant."""
    stmt = select(ApiKey).where(ApiKey.tenant_id == actor.tenant_id).order_by(ApiKey.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.delete("/api-keys/{key_id}")
async def revoke_tenant_api_key(
    key_id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Revokes an API key belonging to the caller's tenant."""
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == actor.tenant_id)
    res = await db.execute(stmt)
    key_obj = res.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=404, detail="API key not found")

    key_obj.is_active = False

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="API_KEY_REVOKED",
        entity_type="api_key",
        entity_id=key_id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"key_name": key_obj.name, "prefix": key_obj.prefix}
    )
    await db.commit()
    return {"status": "revoked", "id": key_id}

@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_tenant_api_key(
    payload: ApiKeyCreate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Generates a secure API key for integration with external UAE banking/enterprise systems."""
    # Block role 'admin' for API keys
    key_role = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
    if key_role.lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: API keys cannot be granted the admin role"
        )

    # Compute expires_at
    expires_at = payload.expires_at
    if not expires_at and payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    raw_key, key_hash, prefix = generate_api_key(actor.tenant_id)
    
    api_key_obj = ApiKey(
        tenant_id=actor.tenant_id,
        name=payload.name,
        prefix=prefix,
        key_hash=key_hash,
        role=key_role,
        is_active=True,
        expires_at=expires_at
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

@router.patch("/{id}", response_model=UserResponse)
async def update_user(
    id: str,
    payload: UserUpdate,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Updates user in tenant. Cannot demote or deactivate the last remaining admin."""
    stmt = select(User).where(User.id == id, User.tenant_id == actor.tenant_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_role = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role) if payload.role else None

    # Check if removing/demoting admin
    if (target_role and target_role != "admin") or (payload.is_active is False):
        if user.role == "admin" and user.is_active:
            admin_count_res = await db.execute(
                select(func.count(User.id)).where(
                    and_(User.tenant_id == actor.tenant_id, User.role == "admin", User.is_active == True, User.id != id)
                )
            )
            other_admins = admin_count_res.scalar() or 0
            if other_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote or deactivate the last remaining admin of the tenant"
                )

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if target_role is not None:
        user.role = target_role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"updated_fields": payload.model_dump(exclude_unset=True, exclude={"password"})}
    )
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{id}")
async def delete_user(
    id: str,
    request: Request,
    actor: AuthenticatedActor = Depends(require_permission(Permission.USER_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """Deletes user in tenant. Cannot delete the last remaining admin."""
    stmt = select(User).where(User.id == id, User.tenant_id == actor.tenant_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == "admin" and user.is_active:
        admin_count_res = await db.execute(
            select(func.count(User.id)).where(
                and_(User.tenant_id == actor.tenant_id, User.role == "admin", User.is_active == True, User.id != id)
            )
        )
        other_admins = admin_count_res.scalar() or 0
        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last remaining admin of the tenant"
            )

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    await log_audit_event(
        db=db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role,
        action="USER_DELETED",
        entity_type="user",
        entity_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"deleted_user_email": user.email, "role": user.role}
    )

    user.is_active = False
    await db.commit()
    return {"detail": "User deactivated successfully", "id": id, "is_active": False}
