from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BoundingBoxSchema(BaseModel):
    x: float
    y: float
    width: float
    height: float

class ExtractedFieldResponse(BaseModel):
    id: str
    field_name: str
    value: Optional[str] = None
    raw_value: Optional[str] = None
    confidence: float
    page_number: int
    bounding_box: Optional[Dict[str, Any]] = None
    is_corrected: bool = False
    corrected_value: Optional[str] = None
    corrected_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentPageResponse(BaseModel):
    id: str
    page_number: int
    image_path: str
    width: int
    height: int

    model_config = ConfigDict(from_attributes=True)

class ValidationResultResponse(BaseModel):
    id: str
    rule_name: str
    passed: bool
    severity: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    document_type_id: Optional[str] = None
    document_type_code: Optional[str] = None
    file_name: str
    file_size: int
    mime_type: str
    status: str
    confidence_score: Optional[float] = None
    language_detected: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    extracted_fields: List[ExtractedFieldResponse] = []
    pages: List[DocumentPageResponse] = []
    validation_results: List[ValidationResultResponse] = []

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]

class FieldCorrectionRequest(BaseModel):
    corrected_value: str
    reason: Optional[str] = None

class RejectDocumentRequest(BaseModel):
    rejection_reason: Optional[str] = None
