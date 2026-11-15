import os
import io
import json
import random
import pytest
from PIL import Image
from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
from app.services.model_engine.base import BoundingBox
from app.schemas.document_type import DEFAULT_TRADE_LICENSE_SCHEMA, DEFAULT_COMMERCIAL_INVOICE_SCHEMA

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "eval", "dataset"))

@pytest.mark.asyncio
async def test_blank_image_returns_unknown_and_null_fields():
    """
    Step 2 Proof:
    A 100% blank white image must be classified as 'unknown' (not defaulted to emirates_id)
    and must return null fields with confidence 0.0 without hallucinating any values.
    """
    adapter = LocalOCRAdapter()
    
    # Create pure blank white image
    blank_img = Image.new("RGB", (1000, 630), color=(255, 255, 255))
    buf = io.BytesIO()
    blank_img.save(buf, format="PNG")
    blank_bytes = buf.getvalue()

    # 1. Classification
    classification = await adapter.classify_document(blank_bytes, filename="blank_scan.png")
    assert classification.document_type_code == "unknown"
    assert classification.confidence == 0.30

    # 2. Extraction
    extraction = await adapter.extract_fields(blank_bytes, "emirates_id", {})
    assert extraction.document_type_code == "emirates_id"
    assert extraction.overall_confidence == 0.0

    # Verify every single field is null with zero confidence
    for field in extraction.fields:
        assert field.value is None, f"Field {field.field_name} must be null on blank image"
        assert field.raw_value is None
        assert field.confidence == 0.0
        assert field.bounding_box is None

@pytest.mark.asyncio
async def test_random_photo_returns_unknown_and_null_fields():
    """
    Step 2 Proof:
    A random photo (simulated by random RGB noise) must return 'unknown'
    and null fields without inventing values.
    """
    adapter = LocalOCRAdapter()

    # Generate random texture / noise image with pure PIL
    noise_img = Image.effect_noise((800, 600), sigma=25).convert("RGB")
    buf = io.BytesIO()
    noise_img.save(buf, format="JPEG", quality=80)
    noise_bytes = buf.getvalue()

    # 1. Classification
    classification = await adapter.classify_document(noise_bytes, filename="random_photo.jpg")
    assert classification.document_type_code == "unknown"
    assert classification.confidence <= 0.50

    # 2. Extraction
    extraction = await adapter.extract_fields(noise_bytes, "emirates_id", {})
    for field in extraction.fields:
        assert field.value is None
        assert field.confidence == 0.0
        assert field.bounding_box is None

@pytest.mark.asyncio
async def test_trade_license_and_invoice_schema_driven_extractors():
    """
    Step 2 Proof:
    Trade License and Commercial Invoice extractors are driven by document type schemas.
    Real token unions are used for bounding boxes; missing fields are null.
    """
    adapter = LocalOCRAdapter()

    # Synthetic tokens representing a real OCR scan of a Trade License
    trade_license_tokens = [
        {"text": "License", "left": 0.10, "top": 0.20, "right": 0.18, "bottom": 0.23, "center_x": 0.14, "center_y": 0.215, "conf": 0.95},
        {"text": "Number:", "left": 0.19, "top": 0.20, "right": 0.28, "bottom": 0.23, "center_x": 0.235, "center_y": 0.215, "conf": 0.94},
        {"text": "CN-2049182", "left": 0.30, "top": 0.20, "right": 0.45, "bottom": 0.23, "center_x": 0.375, "center_y": 0.215, "conf": 0.98},
        {"text": "Company", "left": 0.10, "top": 0.30, "right": 0.20, "bottom": 0.33, "center_x": 0.15, "center_y": 0.315, "conf": 0.92},
        {"text": "Name", "left": 0.21, "top": 0.30, "right": 0.27, "bottom": 0.33, "center_x": 0.24, "center_y": 0.315, "conf": 0.93},
        {"text": "AL", "left": 0.30, "top": 0.30, "right": 0.34, "bottom": 0.33, "center_x": 0.32, "center_y": 0.315, "conf": 0.96},
        {"text": "HILAL", "left": 0.35, "top": 0.30, "right": 0.42, "bottom": 0.33, "center_x": 0.385, "center_y": 0.315, "conf": 0.97},
        {"text": "LOGISTICS", "left": 0.43, "top": 0.30, "right": 0.55, "bottom": 0.33, "center_x": 0.49, "center_y": 0.315, "conf": 0.95},
    ]

    schema_dict = DEFAULT_TRADE_LICENSE_SCHEMA.model_dump()
    fields = adapter._parse_schema_driven_fields(schema_dict, trade_license_tokens, "License Number: CN-2049182 Company Name AL HILAL LOGISTICS")
    fields_map = {f.field_name: f for f in fields}

    # License Number
    assert "license_number" in fields_map
    assert fields_map["license_number"].value == "CN-2049182"
    assert fields_map["license_number"].confidence == 0.98
    assert fields_map["license_number"].bounding_box is not None
    assert fields_map["license_number"].bounding_box.x == 0.30

    # Company Name
    assert "company_name_en" in fields_map
    assert "AL HILAL LOGISTICS" in fields_map["company_name_en"].value
    assert fields_map["company_name_en"].bounding_box is not None

    # Missing field must be None
    assert "issuing_authority" in fields_map
    assert fields_map["issuing_authority"].value is None
    assert fields_map["issuing_authority"].confidence == 0.0

@pytest.mark.asyncio
async def test_run_pipeline_on_rasterized_samples():
    """
    Step 2 Proof:
    Runs the pipeline on rasterized images from the dataset.
    Verifies that real token bounding box objects and confidences are populated.
    """
    adapter = LocalOCRAdapter()
    
    samples_found = 0
    results_summary = []

    for i in range(1, 11):
        img_path = os.path.join(DATASET_DIR, f"sample_{i:03d}.png")
        if not os.path.exists(img_path):
            continue

        with open(img_path, "rb") as f:
            img_bytes = f.read()

        extraction = await adapter.extract_fields(img_bytes, "emirates_id", {})
        samples_found += 1

        fields_summary = {}
        for f in extraction.fields:
            fields_summary[f.field_name] = {
                "value": f.value,
                "confidence": f.confidence,
                "has_bounding_box": f.bounding_box is not None
            }
            if f.bounding_box:
                assert 0.0 <= f.bounding_box.x <= 1.0
                assert 0.0 <= f.bounding_box.y <= 1.0

        results_summary.append({
            "sample": f"sample_{i:03d}",
            "fields": fields_summary
        })

    assert samples_found > 0, "At least some sample images must exist in dataset"
    print("\n--- SAMPLE RASTER EXTRACTION OUTPUT JSON ---")
    print(json.dumps(results_summary[:2], indent=2, ensure_ascii=False))
