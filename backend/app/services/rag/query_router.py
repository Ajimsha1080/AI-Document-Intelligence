import re
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import ExtractedField, Document
from app.services.rag.arabic_normalizer import normalize_arabic_text

FIELD_INTENT_PATTERNS = [
    # Emirates ID number
    (re.compile(r"(emirates\s*id|id\s*number|identity\s*number|رقم\s*الهوية|رقم\s*البطاقة)", re.I), "id_number"),
    # Name
    (re.compile(r"(holder\s*name|full\s*name|\bname\b|الاسم|اسم\s*صاحب\s*الهوية|صاحب\s*الهوية)", re.I), "name"),
    # Expiry Date
    (re.compile(r"(expiry\s*date|expiration|valid\s*until|تاريخ\s*الانتهاء|الصلاحية|تاريخ\s*صلاحية)", re.I), "expiry_date"),
    # Date of Birth
    (re.compile(r"(birth\s*date|date\s*of\s*birth|dob|تاريخ\s*الميلاد|ولادة)", re.I), "date_of_birth"),
    # Trade License Number
    (re.compile(r"(trade\s*license\s*(number|no)|license\s*number|رقم\s*الرخصة)", re.I), "license_number"),
    # Company Name / Trade Name
    (re.compile(r"(company\s*name|trade\s*name|entity\s*name|اسم\s*الشركة|الاسم\s*التجاري)", re.I), "company_name"),
    # TRN / Tax Registration
    (re.compile(r"(trn|tax\s*registration|رقم\s*التسجيل\s*الضريبي)", re.I), "trn"),
    # Invoice Number
    (re.compile(r"(invoice\s*(number|no)|رقم\s*الفاتورة)", re.I), "invoice_number"),
    # Total Amount
    (re.compile(r"(total\s*amount|invoice\s*amount|grand\s*total|المبلغ\s*الإجمالي|إجمالي\s*الفاتورة)", re.I), "total_amount"),
]

async def route_and_lookup_structured_field(
    db: AsyncSession,
    tenant_id: str,
    query: str,
    document_id: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Evaluates whether the user's question maps to a known structured document field.
    If yes, fetches the validated field value with exact coordinates and citations directly.
    Returns (is_structured, result_dict_or_none).
    """
    norm_query = normalize_arabic_text(query)
    target_field = None

    for pattern, field_key in FIELD_INTENT_PATTERNS:
        if pattern.search(norm_query) or pattern.search(query):
            target_field = field_key
            break

    if not target_field:
        return False, None

    # Query ExtractedField with strict tenant isolation
    stmt = (
        select(ExtractedField, Document.file_name)
        .join(Document, ExtractedField.document_id == Document.id)
        .where(
            ExtractedField.tenant_id == tenant_id,
            ExtractedField.field_name.ilike(f"%{target_field}%")
        )
    )
    if document_id:
        stmt = stmt.where(ExtractedField.document_id == document_id)

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

    return True, {
        "mode": "structured_field",
        "field_name": field_record.field_name,
        "answer": f"The {field_record.field_name.replace('_', ' ')} is: {val}",
        "answer_ar": f"قيمة {field_record.field_name}: {val}",
        "confidence": field_record.confidence or 1.0,
        "citations": [citation]
    }
