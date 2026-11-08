from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

class ExtractedFieldData(BaseModel):
    field_name: str
    value: str
    raw_value: str
    confidence: float
    page_number: int
    bounding_box: Optional[BoundingBox] = None

class DocumentPageLayout(BaseModel):
    page_number: int
    width: int
    height: int
    blocks: List[Dict[str, Any]] = []

class ClassificationResult(BaseModel):
    document_type_code: str
    confidence: float
    language: str  # 'ara', 'eng', 'mixed'

class ExtractionResult(BaseModel):
    document_type_code: str
    overall_confidence: float
    fields: List[ExtractedFieldData]
    pages: List[DocumentPageLayout]

class BaseModelProvider(ABC):
    """
    Abstract interface for swappable Document Intelligence model backends.
    Ensures vendor independence and compliance with UAE in-country processing requirements.
    """

    @abstractmethod
    async def classify_document(self, document_bytes: bytes, filename: str) -> ClassificationResult:
        """Classifies document into Emirates ID, Trade License, Invoice, etc."""
        pass

    @abstractmethod
    async def extract_fields(
        self,
        document_bytes: bytes,
        document_type_code: str,
        schema_definition: Dict[str, Any]
    ) -> ExtractionResult:
        """Extracts structured fields with bounding boxes and confidence scores."""
        pass
