from sqlalchemy import Column, String, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TenantAwareMixin, TimestampMixin, generate_uuid, utc_now

class User(Base, TenantAwareMixin, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="reviewer")
    is_active = Column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", back_populates="users")

    __table_args__ = (
        Index("idx_tenant_user_email", "tenant_id", "email", unique=True),
    )

class ApiKey(Base, TenantAwareMixin):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(16), nullable=False)
    key_hash = Column(String(64), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="api_client")
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
