from sqlalchemy import Column, String, JSON, DateTime, Index
from app.core.database import Base
from app.models.base import TenantAwareMixin, generate_uuid, utc_now

class AuditLog(Base, TenantAwareMixin):
    """
    Immutable audit log table for strict compliance with UAE PDPL.
    Records every security-relevant action, document access, field modification,
    export, and deletion event.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True) 
    # e.g., 'DOCUMENT_VIEW', 'DOCUMENT_UPLOAD', 'FIELD_CORRECT', 'DOCUMENT_EXPORT', 'DOCUMENT_DELETE'
    entity_type = Column(String(50), nullable=False, index=True) # e.g. 'document', 'tenant', 'user'
    entity_id = Column(String(36), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True) # Diff or sanitized metadata
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_tenant_action", "tenant_id", "action"),
        Index("idx_audit_tenant_created", "tenant_id", "created_at"),
    )
