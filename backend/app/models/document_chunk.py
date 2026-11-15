from sqlalchemy import Column, String, Integer, Float, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TenantAwareMixin, TimestampMixin, generate_uuid, utc_now

class DocumentChunk(Base, TenantAwareMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, default=1, nullable=False)
    chunk_index = Column(Integer, default=0, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_text_normalized = Column(Text, nullable=False)
    # Bounding box of the chunk on the page: {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.1, "page": 1}
    bounding_box = Column(JSON, nullable=True)
    # Stored embedding vector (list of floats)
    embedding = Column(JSON, nullable=True)
    token_count = Column(Integer, default=0, nullable=False)

    document = relationship("Document", back_populates="chunks")
