from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.core.rbac import UserRole

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.REVIEWER

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    tenant_id: Optional[str] = None # When created by superadmin or during tenant onboarding

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    id: str
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.API_CLIENT
    expires_in_days: Optional[int] = Field(default=90, ge=1, le=365)
    expires_at: Optional[datetime] = None

class ApiKeyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    prefix: str
    role: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    raw_key: Optional[str] = None # Returned only once upon creation

    model_config = ConfigDict(from_attributes=True)
