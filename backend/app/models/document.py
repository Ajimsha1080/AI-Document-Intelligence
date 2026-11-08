from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TenantAwareMixin, TimestampMixin, generate_uuid, utc_now

class Document(Base, TenantAwareMixin, TimestampMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_id = Column(String(36), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(50), default="uploaded", nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)
    uploaded_by = Column(String(36), nullable=True)
    language_detected = Column(String(20), nullable=True)  # 'ara', 'eng', 'mixed'

    tenant = relationship("Tenant", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="document", cascade="all, delete-orphan")

class DocumentPage(Base, TenantAwareMixin):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(500), nullable=False)
    width = Column(Integer, default=1000, nullable=False)
    height = Column(Integer, default=1400, nullable=False)

    document = relationship("Document", back_populates="pages")

class ExtractedField(Base, TenantAwareMixin):
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    value = Column(String(1000), nullable=True)
    raw_value = Column(String(1000), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    # Bounding box in normalized coordinates: {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.05}
    bounding_box = Column(JSON, nullable=True)
    is_corrected = Column(Boolean, default=False, nullable=False)
    corrected_value = Column(String(1000), nullable=True)
    corrected_by = Column(String(36), nullable=True)
    corrected_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="extracted_fields")

class ValidationResult(Base, TenantAwareMixin):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False)
    severity = Column(String(20), default="error", nullable=False) # 'error' or 'warning'
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="validation_results")
