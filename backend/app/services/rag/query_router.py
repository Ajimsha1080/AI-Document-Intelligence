import re
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.document import ExtractedField, Document
from app.services.rag.arabic_normalizer import normalize_arabic_text

FIELD_INTENT_PATTERNS = [
    # Emirates ID number
    (re.compile(r"(emirates\s*id|id\s*number|identity\s*number|رقم\s*الهوية|رقم\s*البطاقة)", re.I), "id_number"),
    # Trade License Number
    (re.compile(r"(trade\s*license\s*(number|no)|license\s*number|رقم\s*الرخصة)", re.I), "license_number"),
    # Specific names BEFORE generic name
    (re.compile(r"(company\s*name|trade\s*name|entity\s*name|اسم\s*الشركة|الاسم\s*التجاري)", re.I), "company_name"),
    (re.compile(r"(vendor\s*name|supplier\s*name|اسم\s*المورد)", re.I), "vendor_name"),
    (re.compile(r"(customer\s*name|client\s*name|buyer\s*name|اسم\s*العميل|اسم\s*المشتري)", re.I), "customer_name"),
    # Generic Name (holder / full / person name)
    (re.compile(r"(holder\s*name|full\s*name|\bname\b|الاسم|اسم\s*صاحب\s*الهوية|صاحب\s*الهوية)", re.I), "name"),
    # Expiry Date
    (re.compile(r"(expiry\s*date|expiration|valid\s*until|تاريخ\s*الانتهاء|الصلاحية|تاريخ\s*صلاحية)", re.I), "expiry_date"),
    # Date of Birth
    (re.compile(r"(birth\s*date|date\s*of\s*birth|dob|تاريخ\s*الميلاد|ولادة)", re.I), "date_of_birth"),
    # TRN / Tax Registration
    (re.compile(r"(trn|tax\s*registration|رقم\s*التسجيل\s*الضريبي)", re.I), "trn"),
    # Invoice Number
    (re.compile(r"(invoice\s*(number|no)|رقم\s*الفاتورة)", re.I), "invoice_number"),
    # Total Amount
    (re.compile(r"(total\s*amount|invoice\s*amount|grand\s*total|المبلغ\s*الإجمالي|إجمالي\s*الفاتورة)", re.I), "total_amount"),
]

# Exact field names mapping to eliminate fuzzy ilike match leakage
INTENT_TO_EXACT_FIELDS = {
    "id_number": ["id_number"],
    "company_name": ["company_name_en", "company_name_ar", "company_name"],
    "vendor_name": ["vendor_name", "vendor_name_en", "vendor_name_ar"],
    "customer_name": ["customer_name", "customer_name_en", "customer_name_ar"],
    "name": ["full_name_ar", "full_name_en", "full_name", "name_ar", "name_en", "name"],
    "license_number": ["license_number"],
    "expiry_date": ["expiry_date"],
    "date_of_birth": ["date_of_birth"],
    "trn": ["trn"],
    "invoice_number": ["invoice_number"],
    "total_amount": ["total_amount"],
}

async def route_and_lookup_structured_field(
    db: AsyncSession,
    tenant_id: str,
    query: str,
    document_id: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Evaluates whether the user's question maps to a known structured document field.
    If yes, fetches the validated field value with exact coordinates and citations directly.
    - Specific patterns evaluated before generic 'name'.
    - Exact field names matched (no fuzzy ilike leakage).
    - Falls back to newest document when document_id is not specified.
    - Preserves confidence 0.0 without coercing to 1.0.
    Returns (is_structured, result_dict_or_none).
    """
    norm_query = normalize_arabic_text(query)
    target_intent = None

    for pattern, field_key in FIELD_INTENT_PATTERNS:
        if pattern.search(norm_query) or pattern.search(query):
            target_intent = field_key
            break

    if not target_intent:
        return False, None

    exact_fields = INTENT_TO_EXACT_FIELDS.get(target_intent, [target_intent])

    # If document_id not provided, resolve to newest document for this tenant that contains these fields
    if not document_id:
        doc_stmt = (
            select(Document.id)
            .join(ExtractedField, ExtractedField.document_id == Document.id)
            .where(
                Document.tenant_id == tenant_id,
                ExtractedField.field_name.in_(exact_fields)
            )
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        newest_doc_id = (await db.execute(doc_stmt)).scalar_one_or_none()
        if not newest_doc_id:
            # Fallback to newest document overall
            overall_stmt = select(Document.id).where(Document.tenant_id == tenant_id).order_by(Document.created_at.desc()).limit(1)
            newest_doc_id = (await db.execute(overall_stmt)).scalar_one_or_none()
            if not newest_doc_id:
                return True, None
        document_id = newest_doc_id

    # Query ExtractedField with strict tenant isolation and exact field matching
    stmt = (
        select(ExtractedField, Document.file_name)
        .join(Document, ExtractedField.document_id == Document.id)
        .where(
            ExtractedField.tenant_id == tenant_id,
            ExtractedField.document_id == document_id,
            ExtractedField.field_name.in_(exact_fields)
        )
        .order_by(Document.created_at.desc())
    )

    res = await db.execute(stmt)
    records = res.all()

    if not records:
        return True, None

    # Pick the best record matching language context (Arabic vs English)
    is_ar_query = bool(re.search(r"[\u0600-\u06FF]", query))
    best_record = None

    for f_rec, fn in records:
        f_val = f_rec.corrected_value or f_rec.value
        if not f_val:
            continue
        if is_ar_query and "_ar" in f_rec.field_name:
            best_record = (f_rec, fn)
            break
        elif not is_ar_query and "_en" in f_rec.field_name:
            best_record = (f_rec, fn)
            break
        elif best_record is None:
            best_record = (f_rec, fn)

    if not best_record:
        return True, None

    field_record, file_name = best_record
    val = field_record.corrected_value or field_record.value

    citation = {
        "chunk_id": field_record.id,
        "document_id": field_record.document_id,
        "page": field_record.page_number,
        "bounding_box": field_record.bounding_box,
        "snippet": f"Field '{field_record.field_name}': {val}"
    }

    # CRITICAL: Preserve 0.0 confidence; do not coerce to 1.0
    field_confidence = field_record.confidence if field_record.confidence is not None else 1.0

    return True, {
        "mode": "structured_field",
        "field_name": field_record.field_name,
        "answer": f"The {field_record.field_name.replace('_', ' ')} is: {val}",
        "answer_ar": f"قيمة {field_record.field_name}: {val}",
        "confidence": field_confidence,
        "citations": [citation]
    }
