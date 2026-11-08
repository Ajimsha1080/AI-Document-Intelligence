from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TenantAwareMixin, TimestampMixin, generate_uuid

class DocumentType(Base, TenantAwareMixin, TimestampMixin):
    __tablename__ = "document_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(64), nullable=False)
    name_en = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    schema_definition = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", back_populates="document_types")
    documents = relationship("Document", back_populates="document_type")

    __table_args__ = (
        Index("idx_tenant_doc_code", "tenant_id", "code", unique=True),
    )
