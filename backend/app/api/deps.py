from typing import AsyncGenerator, Optional
import hashlib
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Header, Request, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.rbac import Permission, has_permission, UserRole
from app.models.user import User, ApiKey
from app.models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

class AuthenticatedActor:
    def __init__(
        self,
        id: str,
        tenant_id: str,
        role: str,
        email: Optional[str] = None,
        is_api_client: bool = False
    ):
        self.id = id
        self.tenant_id = tenant_id
        self.role = role
        self.email = email
        self.is_api_client = is_api_client

async def get_current_actor(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> AuthenticatedActor:
    """
    Authenticates either a user via JWT bearer token or an external client via X-API-Key.
    Enforces tenant context directly.
    """
    # 1. Check API Key
    if x_api_key:
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        result = await db.execute(stmt)
        api_key_obj = result.scalar_one_or_none()
        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        if api_key_obj.expires_at:
            exp = api_key_obj.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired API key",
                )
        # Verify tenant is active
        tenant = await db.get(Tenant, api_key_obj.tenant_id)
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant inactive or suspended")
            
        return AuthenticatedActor(
            id=api_key_obj.id,
            tenant_id=api_key_obj.tenant_id,
            role=api_key_obj.role,
            email=f"apikey:{api_key_obj.prefix}",
            is_api_client=True
        )

    # 2. Check JWT Bearer Token (strictly from Authorization header, never from URL query)
    effective_token = token
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials (Bearer token or X-API-Key required)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(effective_token)
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        role: str = payload.get("role")
        if not user_id or not tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    # Verify user exists in database and belongs to the given tenant
    stmt = select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")

    # Verify tenant is active
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant inactive or suspended")

    return AuthenticatedActor(
        id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
        is_api_client=False
    )

async def get_stream_actor(
    request: Request,
    token: Optional[str] = Query(None),
    header_token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> AuthenticatedActor:
    """
    Validates either a Bearer token or a 60-second single-purpose stream token (?token=...)
    specifically created for SSE connections via POST /api/v1/auth/stream-token.
    Standard full-access JWTs in query params are strictly rejected.
    """
    raw_token = header_token or token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing stream token or Authorization header"
        )

    try:
        payload = decode_access_token(raw_token)
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        role: str = payload.get("role")
        scope: Optional[str] = payload.get("scope")

        # If passed via query param, it MUST have scope == 'sse_stream'
        if token and not header_token and scope != "sse_stream":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security violation: Query parameter tokens must be stream tokens issued via /auth/stream-token"
            )

        if not user_id or not tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid stream token claims")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate stream token")

    stmt = select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")

    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant inactive or suspended")

    return AuthenticatedActor(
        id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
        is_api_client=False
    )

def require_permission(permission: Permission):
    """Dependency factory checking if authenticated actor has required RBAC permission."""
    async def permission_checker(actor: AuthenticatedActor = Depends(get_current_actor)) -> AuthenticatedActor:
        if not has_permission(actor.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{actor.role}' lacks permission '{permission.value}'"
            )
        return actor
    return permission_checker

def require_stream_permission(permission: Permission):
    """Dependency factory checking if SSE stream actor has required RBAC permission."""
    async def permission_checker(actor: AuthenticatedActor = Depends(get_stream_actor)) -> AuthenticatedActor:
        if not has_permission(actor.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{actor.role}' lacks permission '{permission.value}'"
            )
        return actor
    return permission_checker

def require_role(*roles: str):
    """Dependency factory verifying actor belongs to one of the authorized roles."""
    async def role_checker(actor: AuthenticatedActor = Depends(get_current_actor)) -> AuthenticatedActor:
        if actor.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires role in {roles}, but actor has role '{actor.role}'"
            )
        return actor
    return role_checker
