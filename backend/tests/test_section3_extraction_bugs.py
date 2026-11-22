import pytest
import io
import asyncio
from datetime import date, datetime
from PIL import Image
from unittest.mock import patch, MagicMock

from app.pipeline.emirates_id_parser import parse_date_string
from app.pipeline.validator import run_validation_rules
from app.pipeline.preprocessor import ImagePreprocessor
from app.services.model_engine.base import ExtractedFieldData, BoundingBox
from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
from app.services.model_engine.factory import get_model_provider
from app.core.config import settings
from app.models.document import Document, ExtractedField, DocumentPage, ValidationResult
from app.models.document_chunk import DocumentChunk
from app.worker.tasks import process_document_pipeline
from app.services.event_bus import event_bus


def test_parse_date_string_multi_format_and_arabic_digits():
    """Support D/M/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD, YYYY/MM/DD, Arabic digits."""
    # YYYY-MM-DD
    assert parse_date_string("2030-05-14") == "2030-05-14"
    # YYYY/MM/DD
    assert parse_date_string("2030/05/14") == "2030-05-14"
    # DD-MM-YYYY
    assert parse_date_string("14-05-2030") == "2030-05-14"
    # DD.MM.YYYY
    assert parse_date_string("14.05.2030") == "2030-05-14"
    # D/M/YYYY
    assert parse_date_string("5/4/2030") == "2030-04-05"
    assert parse_date_string("14/5/2030") == "2030-05-14"
    # Arabic-Indic digits
    assert parse_date_string("١٤/٠٥/٢٠٣٠") == "2030-05-14"
    assert parse_date_string("٢٠٣٠-٠٥-١٤") == "2030-05-14"
    # Invalid dates
    assert parse_date_string("invalid_date") is None
    assert parse_date_string("99/99/9999") is None


def test_validator_unparseable_date_is_failed_error():
    """validator.py: unparseable date = failed error."""
    fields = [
        ExtractedFieldData(field_name="id_number", value="784-1990-1234567-1", raw_value="784-1990-1234567-1", confidence=0.95),
        ExtractedFieldData(field_name="full_name_ar", value="أحمد المنصوري", raw_value="أحمد المنصوري", confidence=0.95),
        ExtractedFieldData(field_name="full_name_en", value="Ahmed Al Mansoori", raw_value="Ahmed Al Mansoori", confidence=0.95),
        ExtractedFieldData(field_name="expiry_date", value="bad-date-not-parseable", raw_value="bad-date-not-parseable", confidence=0.90),
    ]
    outcomes = run_validation_rules("emirates_id", fields)
    date_errors = [o for o in outcomes if "bad-date" in o["message"] or (not o["passed"] and o["severity"] == "error" and "expiry_date" in o["field_name"])]
    assert len(date_errors) > 0
    assert any(not o["passed"] and o["severity"] == "error" for o in date_errors)


def test_validator_schema_rules_trn_and_not_expired():
    """Test schema rules: not_expired on any type, valid_trn_format (15 digits starting 100)."""
    # 1. Valid TRN
    inv_fields_valid = [
        ExtractedFieldData(field_name="invoice_number", value="INV-2026-001", raw_value="INV-2026-001", confidence=0.90),
        ExtractedFieldData(field_name="trn", value="100123456789012", raw_value="100123456789012", confidence=0.95),
    ]
    outcomes_valid = run_validation_rules("commercial_invoice", inv_fields_valid)
    trn_rule_valid = [o for o in outcomes_valid if o["rule_name"] == "VALID_TRN_FORMAT"]
    assert len(trn_rule_valid) == 1
    assert trn_rule_valid[0]["passed"] is True

    # 2. Invalid TRN (wrong start or wrong length)
    inv_fields_invalid = [
        ExtractedFieldData(field_name="trn", value="200123456789012", raw_value="200123456789012", confidence=0.95),
    ]
    outcomes_invalid = run_validation_rules("commercial_invoice", inv_fields_invalid)
    trn_rule_invalid = [o for o in outcomes_invalid if o["rule_name"] == "VALID_TRN_FORMAT"]
    assert len(trn_rule_invalid) == 1
    assert trn_rule_invalid[0]["passed"] is False
    assert trn_rule_invalid[0]["severity"] == "error"

    # 3. not_expired rule on trade license
    trade_license_fields = [
        ExtractedFieldData(field_name="expiry_date", value="2020-01-01", raw_value="2020-01-01", confidence=0.92),
    ]
    schema_def = {
        "fields": [{"key": "expiry_date", "data_type": "date", "required": True}],
        "rules": [{"rule": "not_expired", "field": "expiry_date"}]
    }
    trade_outcomes = run_validation_rules("uae_trade_license", trade_license_fields, schema_def)
    exp_rule = [o for o in trade_outcomes if o["rule_name"] == "NOT_EXPIRED_EXPIRY_DATE"]
    assert len(exp_rule) == 1
    assert exp_rule[0]["passed"] is False
    assert exp_rule[0]["severity"] == "error"
    assert "expired" in exp_rule[0]["message"].lower()


def test_validator_regex_and_confidence_threshold():
    """Apply validation_regex and confidence_threshold."""
    schema = {
        "fields": [
            {
                "key": "custom_code",
                "required": True,
                "confidence_threshold": 0.85,
                "validation_regex": r"^ABC-\d{3}$"
            }
        ]
    }
    # Low confidence and regex mismatch
    fields = [
        ExtractedFieldData(field_name="custom_code", value="XYZ-12", raw_value="XYZ-12", confidence=0.60)
    ]
    outcomes = run_validation_rules("custom_type", fields, schema)
    regex_outcome = next(o for o in outcomes if "REGEX" in o["rule_name"])
    conf_outcome = next(o for o in outcomes if "CONFIDENCE" in o["rule_name"])
    assert regex_outcome["passed"] is False
    assert regex_outcome["severity"] == "error"
    assert conf_outcome["passed"] is False
    assert conf_outcome["severity"] == "warning"


@pytest.mark.asyncio
async def test_expired_emirates_id_status_needs_review(seeded_data, db_session):
    """Test: expired Emirates ID -> needs_review."""
    tenant_id = seeded_data["tenant_1"].id
    doc = Document(
        tenant_id=tenant_id,
        file_name="expired_eid.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://dummy_path",
        status="uploaded"
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    # Mock storage_service and provider
    from unittest.mock import AsyncMock
    with patch("app.worker.tasks.storage_service.get_document_bytes", return_value=b"fake_image_bytes"), \
         patch("app.worker.tasks.ImagePreprocessor.preprocess_image", return_value=(b"fake_processed", {})), \
         patch("app.worker.tasks.get_model_provider") as mock_gp:

        mock_provider = MagicMock()
        mock_provider.backend_name = "test"
        from app.services.model_engine.base import ClassificationResult, ExtractionResult
        mock_provider.classify_document = AsyncMock(return_value=ClassificationResult(
            document_type_code="emirates_id", confidence=0.98, language="mixed"
        ))
        mock_provider.extract_fields = AsyncMock(return_value=ExtractionResult(
            document_type_code="emirates_id",
            overall_confidence=0.95,
            fields=[
                ExtractedFieldData(field_name="id_number", value="784-1990-1234567-1", raw_value="784-1990-1234567-1", confidence=0.95),
                ExtractedFieldData(field_name="full_name_ar", value="أحمد المنصوري", raw_value="أحمد المنصوري", confidence=0.95),
                ExtractedFieldData(field_name="full_name_en", value="Ahmed Al Mansoori", raw_value="Ahmed Al Mansoori", confidence=0.95),
                ExtractedFieldData(field_name="expiry_date", value="2021-01-01", raw_value="2021-01-01", confidence=0.95),
            ],
            pages=[],
            is_mock=True
        ))
        mock_gp.return_value = mock_provider

        processed_doc = await process_document_pipeline(doc.id, tenant_id, db=db_session)
        assert processed_doc.status == "needs_review"


def test_preprocessor_does_not_rotate_portrait_without_tesseract_osd():
    """Portrait image without Tesseract OSD must NOT be rotated 90 degrees."""
    # Create portrait image: 800w x 1200h (h > w * 1.2)
    img = Image.new("RGB", (800, 1200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    # Preprocess with no OSD
    with patch("app.services.model_engine.local_ocr_adapter.LocalOCRAdapter.get_tesseract_cmd", return_value=None):
        processed_bytes, meta = ImagePreprocessor.preprocess_image(raw_bytes)
        assert meta["rotated_degrees"] == 0
        assert meta["processed_width"] <= meta["processed_height"]
        assert meta["denoised"] is True


def test_local_ocr_adapter_classification_scoring_no_false_emirates_id():
    """Classification must NOT classify as Emirates ID just because 'emirates' is in text."""
    adapter = LocalOCRAdapter()
    invoice_text = "Tax invoice from United Arab Emirates Trading LLC TRN 100987654321098 Total Amount 500 AED"
    with patch.object(adapter, "_get_document_tokens_and_pages") as mock_tokens:
        mock_tokens.return_value = (
            [{"text": word, "conf": 0.95} for word in invoice_text.split()],
            [],
            invoice_text
        )
        with patch.object(adapter, "is_available", return_value=True):
            res = asyncio.run(adapter.classify_document(b"fake_bytes"))
            assert res.document_type_code == "commercial_invoice"
            assert res.document_type_code != "emirates_id"


def test_no_tesseract_returns_empty_fields_with_zero_confidence():
    """No Tesseract -> return empty fields with confidence 0, not mock adapter made-up data."""
    adapter = LocalOCRAdapter()
    with patch.object(adapter, "is_available", return_value=False):
        res = asyncio.run(adapter.extract_fields(b"fake_bytes", "emirates_id", {}))
        assert res.overall_confidence == 0.0
        assert res.is_mock is False
        for f in res.fields:
            assert f.value is None
            assert f.confidence == 0.0


@pytest.mark.asyncio
async def test_worker_tasks_rollback_and_reraise_on_error(seeded_data, db_session):
    """worker/tasks.py: on error rollback, mark failed, emit 'failed' event, re-raise so RQ retries."""
    tenant_id = seeded_data["tenant_1"].id
    doc = Document(
        tenant_id=tenant_id,
        file_name="error_doc.png",
        file_size=1024,
        mime_type="image/png",
        storage_path="local://error_path",
        status="uploaded"
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    with patch("app.worker.tasks.storage_service.get_document_bytes", side_effect=RuntimeError("S3 storage disk crash")):
        with pytest.raises(RuntimeError, match="S3 storage disk crash"):
            await process_document_pipeline(doc.id, tenant_id, db=db_session)

    # Document should be marked failed in DB
    await db_session.refresh(doc)
    assert doc.status == "failed"
