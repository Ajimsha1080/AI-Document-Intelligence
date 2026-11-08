from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class FieldSchema(BaseModel):
    key: str
    name_en: str
    name_ar: str
    data_type: str = "string"  # string, number, date, regex
    required: bool = True
    confidence_threshold: float = 0.85
    validation_regex: Optional[str] = None
    options: Optional[List[str]] = None

class DocumentTypeSchema(BaseModel):
    version: str = "1.0"
    fields: List[FieldSchema]
    rules: Optional[List[Dict[str, Any]]] = None

class DocumentTypeBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name_en: str = Field(..., min_length=2, max_length=255)
    name_ar: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    schema_definition: DocumentTypeSchema

class DocumentTypeCreate(DocumentTypeBase):
    pass

class DocumentTypeResponse(DocumentTypeBase):
    id: str
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Predefined standard schemas for UAE market
DEFAULT_EMIRATES_ID_SCHEMA = DocumentTypeSchema(
    version="1.0",
    fields=[
        FieldSchema(
            key="id_number",
            name_en="Identity Number",
            name_ar="رقم الهوية",
            data_type="regex",
            validation_regex=r"^784-[0-9]{4}-[0-9]{7}-[0-9]{1}$",
            required=True,
            confidence_threshold=0.90
        ),
        FieldSchema(
            key="full_name_ar",
            name_en="Name (Arabic)",
            name_ar="الاسم (بالعربية)",
            data_type="string",
            required=True,
            confidence_threshold=0.85
        ),
        FieldSchema(
            key="full_name_en",
            name_en="Name (English)",
            name_ar="الاسم (بالإنجليزية)",
            data_type="string",
            required=True,
            confidence_threshold=0.85
        ),
        FieldSchema(
            key="nationality_ar",
            name_en="Nationality (Arabic)",
            name_ar="الجنسية (بالعربية)",
            data_type="string",
            required=False,
            confidence_threshold=0.80
        ),
        FieldSchema(
            key="nationality_en",
            name_en="Nationality (English)",
            name_ar="الجنسية (بالإنجليزية)",
            data_type="string",
            required=False,
            confidence_threshold=0.80
        ),
        FieldSchema(
            key="expiry_date",
            name_en="Expiry Date",
            name_ar="تاريخ الانتهاء",
            data_type="date",
            required=True,
            confidence_threshold=0.90
        ),
        FieldSchema(
            key="date_of_birth",
            name_en="Date of Birth",
            name_ar="تاريخ الميلاد",
            data_type="date",
            required=True,
            confidence_threshold=0.85
        )
    ],
    rules=[
        {"rule": "not_expired", "field": "expiry_date"},
        {"rule": "valid_eid_format", "field": "id_number"}
    ]
)

DEFAULT_TRADE_LICENSE_SCHEMA = DocumentTypeSchema(
    version="1.0",
    fields=[
        FieldSchema(
            key="license_number",
            name_en="License Number",
            name_ar="رقم الرخصة",
            data_type="string",
            required=True,
            confidence_threshold=0.88
        ),
        FieldSchema(
            key="company_name_en",
            name_en="Company Name (English)",
            name_ar="الاسم التجاري (بالإنجليزية)",
            data_type="string",
            required=True,
            confidence_threshold=0.85
        ),
        FieldSchema(
            key="company_name_ar",
            name_en="Trade Name (Arabic)",
            name_ar="الاسم التجاري (بالعربية)",
            data_type="string",
            required=True,
            confidence_threshold=0.85
        ),
        FieldSchema(
            key="issuing_authority",
            name_en="Issuing Authority",
            name_ar="سلطة الترخيص",
            data_type="string",
            required=True,
            confidence_threshold=0.85
        ),
        FieldSchema(
            key="expiry_date",
            name_en="Expiry Date",
            name_ar="تاريخ انتهاء الرخصة",
            data_type="date",
            required=True,
            confidence_threshold=0.90
        )
    ],
    rules=[
        {"rule": "not_expired", "field": "expiry_date"}
    ]
)
