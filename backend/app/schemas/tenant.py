from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    tier: str = Field(default="standard")
    retention_days: int = Field(default=365, ge=1, le=3650)
    pii_masking_default: bool = True
    webhook_url: Optional[str] = None

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1, le=3650)
    pii_masking_default: Optional[bool] = None
    webhook_url: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(TenantBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
