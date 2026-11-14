import re
from typing import Dict, Any
from app.services.model_engine.base import (
    BaseModelProvider,
    ClassificationResult,
    ExtractionResult,
    ExtractedFieldData,
    BoundingBox,
    DocumentPageLayout
)

class MockModelAdapter(BaseModelProvider):
    """
    Deterministic model adapter for testing and validation.
    Generates realistic UAE KYC & commercial documents with Arabic & English fields.
    """
    def __init__(self, is_fallback: bool = False):
        self.is_fallback = is_fallback
        self.backend_name = "mock-fallback" if is_fallback else "mock"
        self.is_mock = True

    async def classify_document(self, document_bytes: bytes, filename: str) -> ClassificationResult:
        fn = filename.lower()
        if "eid" in fn or "emirates" in fn or "id" in fn:
            return ClassificationResult(document_type_code="emirates_id", confidence=0.98, language="mixed")
        elif "trade" in fn or "license" in fn or "commercial" in fn:
            return ClassificationResult(document_type_code="uae_trade_license", confidence=0.95, language="mixed")
        else:
            return ClassificationResult(document_type_code="emirates_id", confidence=0.91, language="mixed")

    async def extract_fields(
        self,
        document_bytes: bytes,
        document_type_code: str,
        schema_definition: Dict[str, Any]
    ) -> ExtractionResult:
        pages = [
            DocumentPageLayout(page_number=1, width=1200, height=800, blocks=[])
        ]
        fields = []

        if document_type_code == "emirates_id":
            fields = [
                ExtractedFieldData(
                    field_name="id_number",
                    value="784-1988-1234567-1",
                    raw_value="784-1988-1234567-1",
                    confidence=0.99,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.25, y=0.48, width=0.50, height=0.08)
                ),
                ExtractedFieldData(
                    field_name="full_name_ar",
                    value="سالم راشد سيف الشامسي",
                    raw_value="سالم راشد سيف الشامسي",
                    confidence=0.96,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.25, y=0.25, width=0.45, height=0.06)
                ),
                ExtractedFieldData(
                    field_name="full_name_en",
                    value="SALEM RASHED SAIF AL SHAMSI",
                    raw_value="SALEM RASHED SAIF AL SHAMSI",
                    confidence=0.97,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.25, y=0.32, width=0.55, height=0.06)
                ),
                ExtractedFieldData(
                    field_name="nationality_ar",
                    value="الإمارات العربية المتحدة",
                    raw_value="الإمارات العربية المتحدة",
                    confidence=0.94,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.25, y=0.40, width=0.30, height=0.05)
                ),
                ExtractedFieldData(
                    field_name="nationality_en",
                    value="United Arab Emirates",
                    raw_value="United Arab Emirates",
                    confidence=0.95,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.58, y=0.40, width=0.30, height=0.05)
                ),
                ExtractedFieldData(
                    field_name="date_of_birth",
                    value="1988-04-15",
                    raw_value="15/04/1988",
                    confidence=0.92,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.25, y=0.60, width=0.22, height=0.05)
                ),
                ExtractedFieldData(
                    field_name="expiry_date",
                    value="2028-04-14",
                    raw_value="14/04/2028",
                    confidence=0.93,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.60, y=0.60, width=0.22, height=0.05)
                ),
            ]
        elif document_type_code == "uae_trade_license":
            fields = [
                ExtractedFieldData(
                    field_name="license_number",
                    value="CN-1029384",
                    raw_value="CN-1029384",
                    confidence=0.98,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.20, y=0.20, width=0.30, height=0.05)
                ),
                ExtractedFieldData(
                    field_name="company_name_en",
                    value="GULF HORIZON LOGISTICS L.L.C.",
                    raw_value="GULF HORIZON LOGISTICS L.L.C.",
                    confidence=0.95,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.20, y=0.28, width=0.60, height=0.06)
                ),
                ExtractedFieldData(
                    field_name="company_name_ar",
                    value="شركة أفق الخليج للخدمات اللوجستية ذ.م.م",
                    raw_value="شركة أفق الخليج للخدمات اللوجستية ذ.م.م",
                    confidence=0.94,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.20, y=0.36, width=0.60, height=0.06)
                ),
                ExtractedFieldData(
                    field_name="issuing_authority",
                    value="Dubai Department of Economy and Tourism (DET)",
                    raw_value="دائرة الاقتصاد والسياحة بدبي",
                    confidence=0.92,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.20, y=0.45, width=0.50, height=0.05)
                ),
                ExtractedFieldData(
                    field_name="expiry_date",
                    value="2027-11-30",
                    raw_value="30/11/2027",
                    confidence=0.91,
                    page_number=1,
                    bounding_box=BoundingBox(x=0.20, y=0.55, width=0.25, height=0.05)
                )
            ]

        avg_conf = sum(f.confidence for f in fields) / len(fields) if fields else 0.0

        return ExtractionResult(
            document_type_code=document_type_code,
            overall_confidence=round(avg_conf, 2),
            fields=fields,
            pages=pages,
            is_mock=True,
            backend_used=self.backend_name
        )
