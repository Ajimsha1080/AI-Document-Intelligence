import io
import os
import re
import shutil
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

from app.services.model_engine.base import (
    BaseModelProvider,
    ClassificationResult,
    ExtractionResult,
    ExtractedFieldData,
    BoundingBox,
    DocumentPageLayout
)
from app.pipeline.preprocessor import ImagePreprocessor
from app.pipeline.emirates_id_parser import (
    normalize_arabic_digits,
    validate_emirates_id_number,
    parse_date_string
)

logger = logging.getLogger("local_ocr_adapter")

class LocalOCRAdapter(BaseModelProvider):
    """
    Air-gapped Local OCR & Document Extraction Adapter.
    Uses Tesseract (ara+eng) or in-memory OCR layout analysis.
    Zero outbound network calls at runtime.
    Caches OCR extraction per document bytes so OCR and preprocessing run only once.
    """
    backend_name = "local"
    is_mock = False

    def __init__(self):
        self._cache: Dict[str, Tuple[List[Dict[str, Any]], List[DocumentPageLayout], str]] = {}

    @classmethod
    def get_tesseract_cmd(cls) -> Optional[str]:
        user_home = os.path.expanduser("~")
        standard_paths = [
            shutil.which("tesseract"),
            os.path.join(user_home, "Tesseract-OCR", "tesseract.exe"),
            os.path.join(user_home, "AppData", "Local", "Programs", "Tesseract-OCR", "tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        for p in standard_paths:
            if p and os.path.exists(p):
                return p
        return None

    @classmethod
    def is_available(cls) -> bool:
        """Checks if local OCR binary is installed and accessible."""
        return cls.get_tesseract_cmd() is not None

    @classmethod
    def get_ocr_info(cls) -> Dict[str, Any]:
        """Returns OCR engine name and list of loaded languages."""
        tess_cmd = cls.get_tesseract_cmd()
        if not tess_cmd:
            return {"ocr_engine": "none", "ocr_languages": []}
        try:
            import subprocess
            res = subprocess.run([tess_cmd, "--list-langs"], capture_output=True, text=True, timeout=5)
            langs = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.lower().startswith("list of")]
            return {"ocr_engine": "tesseract", "ocr_languages": langs}
        except Exception as e:
            logger.warning(f"Failed to query tesseract languages: {e}")
            return {"ocr_engine": "tesseract", "ocr_languages": []}

    def _get_tesseract_cmd(self) -> Optional[str]:
        return self.get_tesseract_cmd()

    def _get_document_tokens_and_pages(
        self,
        document_bytes: bytes
    ) -> Tuple[List[Dict[str, Any]], List[DocumentPageLayout], str]:
        """
        Extracts OCR tokens and pages once per document with caching.
        Handles multi-page PDFs (up to 10 pages).
        Keeps ALL OCR tokens (not truncated to 50).
        """
        doc_hash = hashlib.sha256(document_bytes).hexdigest()
        if doc_hash in self._cache:
            return self._cache[doc_hash]

        if not self.is_available():
            empty_pages = [DocumentPageLayout(page_number=1, width=1000, height=600, blocks=[])]
            self._cache[doc_hash] = ([], empty_pages, "")
            return [], empty_pages, ""

        all_tokens: List[Dict[str, Any]] = []
        pages: List[DocumentPageLayout] = []

        if document_bytes.startswith(b"%PDF"):
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(document_bytes)
                num_pages = min(10, len(pdf))
                for page_idx in range(num_pages):
                    page = pdf[page_idx]
                    pil_img = page.render(scale=2.0).to_pil()
                    img_w, img_h = pil_img.size
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    p_bytes = buf.getvalue()
                    try:
                        p_tokens = self._extract_tokens_with_boxes(p_bytes, img_w, img_h, page_number=page_idx + 1)
                    except TypeError:
                        p_tokens = self._extract_tokens_with_boxes(p_bytes, img_w, img_h)
                    all_tokens.extend(p_tokens)
                    pages.append(DocumentPageLayout(
                        page_number=page_idx + 1,
                        width=img_w,
                        height=img_h,
                        blocks=[{"text": t["text"], "box": t["box"]} for t in p_tokens]
                    ))
            except Exception as e:
                logger.warning(f"Failed to extract tokens from PDF: {e}")
        else:
            try:
                img = Image.open(io.BytesIO(document_bytes))
                img_w, img_h = img.size
            except Exception:
                img_w, img_h = 1000, 600

            try:
                tokens = self._extract_tokens_with_boxes(document_bytes, img_w, img_h)
            except TypeError:
                tokens = self._extract_tokens_with_boxes(document_bytes, img_w, img_h, page_number=1)
            all_tokens = tokens
            pages = [
                DocumentPageLayout(
                    page_number=1,
                    width=img_w,
                    height=img_h,
                    blocks=[{"text": t["text"], "box": t["box"]} for t in tokens]
                )
            ]

        full_text = " ".join(t.get("text", "") for t in all_tokens)
        self._cache[doc_hash] = (all_tokens, pages, full_text)
        return all_tokens, pages, full_text

    async def classify_document(self, document_bytes: bytes, filename: str = "") -> ClassificationResult:
        """
        Classifies document strictly by examining scored specific textual markers from real OCR text.
        Never defaults everything to 'emirates_id' due to matching 'emirates'.
        Requires specific markers like:
        - 784-XXXX-XXXXXXX-X / 'identity card' -> emirates_id
        - 'license no' / 'رخصة' -> uae_trade_license
        - 'invoice' / 'TRN' / 'فاتورة' -> commercial_invoice
        Otherwise returns 'unknown'.
        """
        if not self.is_available():
            return ClassificationResult(document_type_code="unknown", confidence=0.0, language="none")

        tokens, _, full_text = self._get_document_tokens_and_pages(document_bytes)
        combined = full_text.lower()
        norm_combined = normalize_arabic_digits(combined)

        # Detect language
        has_arabic = bool(re.search(r"[\u0600-\u06FF]", full_text))
        has_english = bool(re.search(r"[a-zA-Z]", full_text))
        if has_arabic and has_english:
            lang = "mixed"
        elif has_arabic:
            lang = "ara"
        elif has_english:
            lang = "eng"
        else:
            lang = "mixed"

        scores = {"emirates_id": 0, "uae_trade_license": 0, "commercial_invoice": 0}

        # 1. Emirates ID Markers (Require specific markers, never match bare "emirates")
        if re.search(r"\b784[\-\s]?\d{4}[\-\s]?\d{7}[\-\s]?\d\b", norm_combined):
            scores["emirates_id"] += 12
        elif "784-" in norm_combined or "784 " in norm_combined:
            scores["emirates_id"] += 6

        if any(m in combined for m in ["identity card", "resident identity card", "بطاقة هوية", "الهوية الإماراتية", "بطاقة الهوية"]):
            scores["emirates_id"] += 8

        # 2. Trade License Markers
        if any(m in combined for m in ["license no", "trade license", "commercial license", "professional license"]):
            scores["uae_trade_license"] += 8
        if any(m in combined for m in ["رخصة تجارية", "رخصة مهنية", "رخصة", "تنمية اقتصادية", "دائرة التنمية", "economic development"]):
            scores["uae_trade_license"] += 8

        # 3. Commercial Invoice Markers
        if any(m in combined for m in ["tax invoice", "commercial invoice", "invoice no", "فاتورة ضريبية", "فاتورة"]):
            scores["commercial_invoice"] += 8
        if any(m in combined for m in ["trn", "tax registration number", "رقم التسجيل الضريبي"]):
            scores["commercial_invoice"] += 8
        if any(m in combined for m in ["vat amount", "total amount", "المبلغ الإجمالي"]):
            scores["commercial_invoice"] += 4

        best_type, best_score = max(scores.items(), key=lambda item: item[1])

        if best_score >= 6:
            conf = min(0.98, round(0.70 + (best_score * 0.03), 2))
            return ClassificationResult(document_type_code=best_type, confidence=conf, language=lang)

        return ClassificationResult(document_type_code="unknown", confidence=0.30, language=lang)

    @staticmethod
    def _union_token_boxes(tokens: List[Dict[str, Any]]) -> Optional[BoundingBox]:
        """Builds field bounding box from actual OCR tokens (union of token boxes), normalized to 0-1."""
        if not tokens:
            return None
        min_x = min(t["left"] for t in tokens)
        min_y = min(t["top"] for t in tokens)
        max_r = max(t["right"] for t in tokens)
        max_b = max(t["bottom"] for t in tokens)
        return BoundingBox(
            x=round(min_x, 4),
            y=round(min_y, 4),
            width=round(max(0.001, max_r - min_x), 4),
            height=round(max(0.001, max_b - min_y), 4)
        )

    @staticmethod
    def _average_token_confidence(tokens: List[Dict[str, Any]]) -> float:
        """Computes field confidence from OCR token confidences."""
        if not tokens:
            return 0.0
        return round(sum(t["conf"] for t in tokens) / len(tokens), 2)

    async def extract_fields(
        self,
        document_bytes: bytes,
        document_type_code: str,
        schema_definition: Dict[str, Any]
    ) -> ExtractionResult:
        """
        Extracts fields using local OCR tokens.
        If Tesseract is not installed, returns empty fields with confidence 0.0.
        """
        # If no Tesseract, return empty fields with 0 confidence
        if not self.is_available():
            expected_keys = []
            if document_type_code == "emirates_id":
                expected_keys = ["id_number", "full_name_ar", "full_name_en", "nationality_ar", "nationality_en", "expiry_date", "date_of_birth"]
            elif schema_definition and "fields" in schema_definition:
                expected_keys = [f.get("key") or f.get("name") for f in schema_definition["fields"] if f.get("key") or f.get("name")]
            empty_fields = [
                ExtractedFieldData(field_name=k, value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None)
                for k in expected_keys
            ]
            return ExtractionResult(
                document_type_code=document_type_code,
                overall_confidence=0.0,
                fields=empty_fields,
                pages=[DocumentPageLayout(page_number=1, width=1000, height=600, blocks=[])],
                is_mock=False,
                backend_used="local_no_ocr"
            )

        # Retrieve cached or extracted tokens and pages (runs once)
        tokens, pages, full_text = self._get_document_tokens_and_pages(document_bytes)
        normalized_full_text = normalize_arabic_digits(full_text)

        fields: List[ExtractedFieldData] = []

        if document_type_code == "emirates_id":
            fields = self._parse_emirates_id(tokens, full_text, normalized_full_text)
        elif document_type_code == "uae_trade_license":
            from app.schemas.document_type import DEFAULT_TRADE_LICENSE_SCHEMA
            eff_schema = schema_definition if (schema_definition and schema_definition.get("fields")) else DEFAULT_TRADE_LICENSE_SCHEMA.model_dump()
            fields = self._parse_schema_driven_fields(eff_schema, tokens, full_text)
        elif document_type_code == "commercial_invoice":
            from app.schemas.document_type import DEFAULT_COMMERCIAL_INVOICE_SCHEMA
            eff_schema = schema_definition if (schema_definition and schema_definition.get("fields")) else DEFAULT_COMMERCIAL_INVOICE_SCHEMA.model_dump()
            fields = self._parse_schema_driven_fields(eff_schema, tokens, full_text)
        else:
            fields = self._parse_schema_driven_fields(schema_definition or {}, tokens, full_text)

        found_fields = [f for f in fields if f.value is not None]
        overall_conf = (
            sum(f.confidence for f in found_fields) / len(found_fields)
            if found_fields else 0.0
        )

        return ExtractionResult(
            document_type_code=document_type_code,
            overall_confidence=round(overall_conf, 2),
            fields=fields,
            pages=pages,
            is_mock=False,
            backend_used=self.backend_name
        )

    def _extract_tokens_with_boxes(
        self,
        img_bytes: bytes,
        img_w: int,
        img_h: int,
        page_number: int = 1
    ) -> List[Dict[str, Any]]:
        """Extracts OCR word tokens and bounding boxes from raster image via Tesseract."""
        tess_cmd = self.get_tesseract_cmd()
        tokens = []
        if not tess_cmd:
            return tokens

        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tess_cmd
            img = Image.open(io.BytesIO(img_bytes))
            data = pytesseract.image_to_data(img, lang="ara+eng", output_type=pytesseract.Output.DICT)
            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                text = str(data["text"][i]).strip()
                raw_conf = data["conf"][i]
                conf_val = float(raw_conf) if str(raw_conf).strip() not in ["-1", ""] else -1.0
                if text and conf_val >= 0:
                    left = float(data["left"][i])
                    top = float(data["top"][i])
                    width = float(data["width"][i])
                    height = float(data["height"][i])
                    norm_x = round(left / img_w, 4)
                    norm_y = round(top / img_h, 4)
                    norm_w = round(width / img_w, 4)
                    norm_h = round(height / img_h, 4)
                    norm_conf = max(0.0, min(1.0, round(conf_val / 100.0, 4)))
                    tokens.append({
                        "text": text,
                        "box": BoundingBox(
                            x=norm_x,
                            y=norm_y,
                            width=norm_w,
                            height=norm_h,
                            page=page_number
                        ),
                        "conf": norm_conf,
                        "left": norm_x,
                        "top": norm_y,
                        "right": round(norm_x + norm_w, 4),
                        "bottom": round(norm_y + norm_h, 4),
                        "center_x": round(norm_x + norm_w / 2, 4),
                        "center_y": round(norm_y + norm_h / 2, 4),
                        "page_number": page_number,
                        "line_num": data.get("line_num", [0])[i],
                        "block_num": data.get("block_num", [0])[i]
                    })
        except Exception as e:
            logger.warning(f"Tesseract token extraction failed: {e}")

        return tokens

    def _parse_emirates_id(
        self,
        tokens: List[Dict[str, Any]],
        full_text: str,
        norm_text: str
    ) -> List[ExtractedFieldData]:
        """Parses Emirates ID fields by layout proximity and token bounding box unions."""
        fields: List[ExtractedFieldData] = []

        # 1. ID Number (784-YYYY-NNNNNNN-C)
        matched_id_tokens: List[Dict[str, Any]] = []
        raw_id: Optional[str] = None
        formatted_id: Optional[str] = None
        is_valid_id = False

        for t in tokens:
            norm_t = normalize_arabic_digits(t["text"])
            m = re.search(r"(?:784[\-\s]?)?(?:\d{4})[\-\s]?(?:\d{7})[\-\s]?(?:\d)", norm_t)
            if not m and "784" in norm_t:
                m = re.search(r"784[\-\s]?\d{2,4}[\-\s]?[0-9A-Za-z\!]+", norm_t)
            if m:
                candidate = m.group(0)
                valid, fid, _ = validate_emirates_id_number(candidate)
                if valid or len(re.sub(r"\D", "", candidate)) >= 5:
                    matched_id_tokens = [t]
                    raw_id = t["text"]
                    clean_cand = re.sub(r"[^\d\-]", "", candidate)
                    formatted_id = fid if valid else (clean_cand if len(clean_cand) >= 7 else candidate)
                    is_valid_id = valid
                    break

        if not matched_id_tokens:
            for i in range(len(tokens)):
                window = []
                acc_text = ""
                for j in range(i, min(i + 7, len(tokens))):
                    if abs(tokens[j]["center_y"] - tokens[i]["center_y"]) > 0.035:
                        break
                    window.append(tokens[j])
                    acc_text += normalize_arabic_digits(tokens[j]["text"])
                    m = re.search(r"(?:784[\-\s]?)?(?:\d{4})[\-\s]?(?:\d{7})[\-\s]?(?:\d)", acc_text)
                    if m:
                        candidate = m.group(0)
                        valid, fid, _ = validate_emirates_id_number(candidate)
                        if valid:
                            matched_id_tokens = window
                            raw_id = " ".join(tok["text"] for tok in window)
                            formatted_id = fid
                            is_valid_id = True
                            break
                if matched_id_tokens:
                    break

        if matched_id_tokens:
            fields.append(ExtractedFieldData(
                field_name="id_number",
                value=formatted_id if is_valid_id else raw_id,
                raw_value=raw_id,
                confidence=self._average_token_confidence(matched_id_tokens),
                page_number=1,
                bounding_box=self._union_token_boxes(matched_id_tokens)
            ))
        else:
            fields.append(ExtractedFieldData(field_name="id_number", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 2. English Full Name
        en_stop_words = {"name", "nationality", "sex", "card", "identity", "united", "arab", "emirates", "federal", "authority", "citizenship", "date", "birth", "dob", "expiry", "signature", "holder", "resident", "citizen"}
        matched_en_name_tokens: List[Dict[str, Any]] = []

        name_labels = [t for t in tokens if t["text"].lower().strip(":") == "name" or t["text"].lower().startswith("name:")]
        if name_labels:
            lbl = name_labels[0]
            right_tokens = [
                t for t in tokens
                if abs(t["center_y"] - lbl["center_y"]) < 0.035
                and t["left"] >= lbl["right"] - 0.02
                and t["text"].lower().strip(":") not in en_stop_words
                and re.match(r"^[A-Za-z\'-]+$", t["text"].strip(":"))
            ]
            if right_tokens:
                matched_en_name_tokens = right_tokens
            else:
                below_tokens = [
                    t for t in tokens
                    if 0 < t["top"] - lbl["bottom"] < 0.06
                    and t["text"].lower().strip(":") not in en_stop_words
                    and re.match(r"^[A-Za-z\'-]+$", t["text"].strip(":"))
                ]
                if below_tokens:
                    matched_en_name_tokens = below_tokens

        if not matched_en_name_tokens:
            for i in range(len(tokens)):
                candidate_seq = []
                for j in range(i, min(i + 5, len(tokens))):
                    if abs(tokens[j]["center_y"] - tokens[i]["center_y"]) > 0.035:
                        break
                    txt = tokens[j]["text"].strip(":")
                    if txt.lower() not in en_stop_words and re.match(r"^[A-Z][a-zA-Z]{1,}$", txt):
                        candidate_seq.append(tokens[j])
                    else:
                        break
                if len(candidate_seq) >= 2:
                    matched_en_name_tokens = candidate_seq
                    break

        if matched_en_name_tokens:
            en_val = " ".join(t["text"].strip(":") for t in matched_en_name_tokens).strip()
            en_box = self._union_token_boxes(matched_en_name_tokens)
            en_conf = self._average_token_confidence(matched_en_name_tokens)
            fields.append(ExtractedFieldData(field_name="full_name_en", value=en_val, raw_value=en_val, confidence=en_conf, page_number=1, bounding_box=en_box))
            fields.append(ExtractedFieldData(field_name="name_en", value=en_val, raw_value=en_val, confidence=en_conf, page_number=1, bounding_box=en_box))
        else:
            fields.append(ExtractedFieldData(field_name="full_name_en", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))
            fields.append(ExtractedFieldData(field_name="name_en", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 3. Arabic Full Name
        ar_stop_words = {"الاسم", "اسم", "الجنسية", "الهوية", "بطاقة", "الميلاد", "تاريخ", "الانتهاء", "الجنس", "دولة", "الإمارات", "العربية", "المتحدة", "هيئة", "الاتحادية", "للهوية", "والجنسية"}
        matched_ar_name_tokens: List[Dict[str, Any]] = []

        ar_name_labels = [t for t in tokens if "الاسم" in t["text"]]
        if ar_name_labels:
            lbl = ar_name_labels[0]
            same_line_ar = [
                t for t in tokens
                if abs(t["center_y"] - lbl["center_y"]) < 0.035
                and t != lbl
                and t["text"].strip(":") not in ar_stop_words
                and re.match(r"^[\u0621-\u064A]+$", t["text"].strip(":"))
            ]
            if same_line_ar:
                matched_ar_name_tokens = same_line_ar
            else:
                below_ar = [
                    t for t in tokens
                    if 0 < t["top"] - lbl["bottom"] < 0.06
                    and t["text"].strip(":") not in ar_stop_words
                    and re.match(r"^[\u0621-\u064A]+$", t["text"].strip(":"))
                ]
                if below_ar:
                    matched_ar_name_tokens = below_ar

        if not matched_ar_name_tokens:
            for i in range(len(tokens)):
                candidate_seq = []
                for j in range(i, min(i + 5, len(tokens))):
                    if abs(tokens[j]["center_y"] - tokens[i]["center_y"]) > 0.035:
                        break
                    txt = tokens[j]["text"].strip(":")
                    if txt not in ar_stop_words and re.match(r"^[\u0621-\u064A]{2,}$", txt):
                        candidate_seq.append(tokens[j])
                    else:
                        break
                if len(candidate_seq) >= 2:
                    matched_ar_name_tokens = candidate_seq
                    break

        if matched_ar_name_tokens:
            ar_val = " ".join(t["text"].strip(":") for t in matched_ar_name_tokens).strip()
            ar_box = self._union_token_boxes(matched_ar_name_tokens)
            ar_conf = self._average_token_confidence(matched_ar_name_tokens)
            fields.append(ExtractedFieldData(field_name="full_name_ar", value=ar_val, raw_value=ar_val, confidence=ar_conf, page_number=1, bounding_box=ar_box))
            fields.append(ExtractedFieldData(field_name="name_ar", value=ar_val, raw_value=ar_val, confidence=ar_conf, page_number=1, bounding_box=ar_box))
        else:
            fields.append(ExtractedFieldData(field_name="full_name_ar", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))
            fields.append(ExtractedFieldData(field_name="name_ar", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 4. Nationality (Both English and Arabic: nationality_en, nationality_ar)
        # Stricter: Only from explicit proximity to nationality label, never random tokens
        matched_en_nat_tokens: List[Dict[str, Any]] = []
        matched_ar_nat_tokens: List[Dict[str, Any]] = []

        nat_en_labels = [t for t in tokens if "nationality" in t["text"].lower()]
        if nat_en_labels:
            lbl = nat_en_labels[0]
            cand = [
                t for t in tokens
                if (abs(t["center_y"] - lbl["center_y"]) < 0.035 and t["left"] >= lbl["right"] - 0.02)
                or (0 < t["top"] - lbl["bottom"] < 0.06 and abs(t["center_x"] - lbl["center_x"]) < 0.25)
            ]
            valid_cand = [c for c in cand if c["text"].lower().strip(":") not in {"date", "birth", "dob", "sex", "expiry"} and re.match(r"^[A-Za-z]+$", c["text"].strip(":"))]
            if valid_cand:
                matched_en_nat_tokens = valid_cand

        nat_ar_labels = [t for t in tokens if "الجنسية" in t["text"]]
        if nat_ar_labels:
            lbl = nat_ar_labels[0]
            cand = [
                t for t in tokens
                if (abs(t["center_y"] - lbl["center_y"]) < 0.035 and t != lbl)
                or (0 < t["top"] - lbl["bottom"] < 0.06 and abs(t["center_x"] - lbl["center_x"]) < 0.25)
            ]
            valid_cand = [c for c in cand if c["text"].strip(":") not in ar_stop_words and re.match(r"^[\u0621-\u064A]+$", c["text"].strip(":"))]
            if valid_cand:
                matched_ar_nat_tokens = valid_cand

        # English nationality
        if matched_en_nat_tokens:
            nat_en_val = " ".join(t["text"].strip(":") for t in matched_en_nat_tokens).strip()
            conf = self._average_token_confidence(matched_en_nat_tokens)
            box = self._union_token_boxes(matched_en_nat_tokens)
            fields.append(ExtractedFieldData(field_name="nationality_en", value=nat_en_val, raw_value=nat_en_val, confidence=conf, page_number=1, bounding_box=box))
            fields.append(ExtractedFieldData(field_name="nationality", value=nat_en_val, raw_value=nat_en_val, confidence=conf, page_number=1, bounding_box=box))
        else:
            fields.append(ExtractedFieldData(field_name="nationality_en", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))
            fields.append(ExtractedFieldData(field_name="nationality", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # Arabic nationality
        if matched_ar_nat_tokens:
            nat_ar_val = " ".join(t["text"].strip(":") for t in matched_ar_nat_tokens).strip()
            conf = self._average_token_confidence(matched_ar_nat_tokens)
            box = self._union_token_boxes(matched_ar_nat_tokens)
            fields.append(ExtractedFieldData(field_name="nationality_ar", value=nat_ar_val, raw_value=nat_ar_val, confidence=conf, page_number=1, bounding_box=box))
        else:
            fields.append(ExtractedFieldData(field_name="nationality_ar", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 5. Date of Birth
        matched_dob_tokens: List[Dict[str, Any]] = []
        dob_labels = [t for t in tokens if any(k in t["text"].lower() for k in ["dob", "birth", "الميلاد"])]
        if dob_labels:
            lbl = dob_labels[0]
            cand = [
                t for t in tokens
                if (abs(t["center_y"] - lbl["center_y"]) < 0.035 and t["left"] >= lbl["right"] - 0.02)
                or (0 < t["top"] - lbl["bottom"] < 0.06 and abs(t["center_x"] - lbl["center_x"]) < 0.25)
            ]
            for c in cand:
                norm_c = normalize_arabic_digits(c["text"])
                if re.search(r"\d{1,4}[\/\.\-]\d{1,2}[\/\.\-]\d{1,4}", norm_c):
                    matched_dob_tokens = [c]
                    break

        if matched_dob_tokens:
            raw_dob = matched_dob_tokens[0]["text"]
            dob_val = parse_date_string(normalize_arabic_digits(raw_dob)) or raw_dob
            fields.append(ExtractedFieldData(
                field_name="date_of_birth",
                value=dob_val,
                raw_value=raw_dob,
                confidence=self._average_token_confidence(matched_dob_tokens),
                page_number=1,
                bounding_box=self._union_token_boxes(matched_dob_tokens)
            ))
        else:
            fields.append(ExtractedFieldData(field_name="date_of_birth", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 6. Expiry Date
        matched_exp_tokens: List[Dict[str, Any]] = []
        exp_labels = [t for t in tokens if any(k in t["text"].lower() for k in ["expiry", "الانتهاء"])]
        if exp_labels:
            lbl = exp_labels[0]
            cand = [
                t for t in tokens
                if (abs(t["center_y"] - lbl["center_y"]) < 0.035 and t["left"] >= lbl["right"] - 0.02)
                or (0 < t["top"] - lbl["bottom"] < 0.06 and abs(t["center_x"] - lbl["center_x"]) < 0.25)
            ]
            for c in cand:
                norm_c = normalize_arabic_digits(c["text"])
                if re.search(r"\d{1,4}[\/\.\-]\d{1,2}[\/\.\-]\d{1,4}", norm_c):
                    matched_exp_tokens = [c]
                    break

        if matched_exp_tokens:
            raw_exp = matched_exp_tokens[0]["text"]
            exp_val = parse_date_string(normalize_arabic_digits(raw_exp)) or raw_exp
            fields.append(ExtractedFieldData(
                field_name="expiry_date",
                value=exp_val,
                raw_value=raw_exp,
                confidence=self._average_token_confidence(matched_exp_tokens),
                page_number=1,
                bounding_box=self._union_token_boxes(matched_exp_tokens)
            ))
        else:
            fields.append(ExtractedFieldData(field_name="expiry_date", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        # 7. Sex (M / F) - strictly next to sex label, no random tokens
        matched_sex_tokens: List[Dict[str, Any]] = []
        sex_labels = [t for t in tokens if any(k in t["text"].lower() for k in ["sex", "الجنس"])]
        if sex_labels:
            lbl = sex_labels[0]
            cand = [
                t for t in tokens
                if (abs(t["center_y"] - lbl["center_y"]) < 0.035 and t["left"] >= lbl["right"] - 0.02)
                or (0 < t["top"] - lbl["bottom"] < 0.06 and abs(t["center_x"] - lbl["center_x"]) < 0.20)
            ]
            for c in cand:
                c_clean = c["text"].upper().strip(":")
                if c_clean in ["M", "F", "ذكر", "أنثى"]:
                    matched_sex_tokens = [c]
                    break

        if matched_sex_tokens:
            raw_sex = matched_sex_tokens[0]["text"].upper().strip(":")
            sex_val = "M" if raw_sex in ["M", "ذكر"] else "F"
            fields.append(ExtractedFieldData(
                field_name="sex",
                value=sex_val,
                raw_value=raw_sex,
                confidence=self._average_token_confidence(matched_sex_tokens),
                page_number=1,
                bounding_box=self._union_token_boxes(matched_sex_tokens)
            ))
        else:
            fields.append(ExtractedFieldData(field_name="sex", value=None, raw_value=None, confidence=0.0, page_number=1, bounding_box=None))

        return fields

    def _parse_schema_driven_fields(
        self,
        schema: Dict[str, Any],
        tokens: List[Dict[str, Any]],
        full_text: str
    ) -> List[ExtractedFieldData]:
        """
        Extracts structured fields driven by document type schema definition.
        Enforces stricter whole-word label matching (3+ chars whole words).
        Uses spatial proximity layout to associate labels with values.
        """
        fields: List[ExtractedFieldData] = []
        schema_fields = schema.get("fields", []) if isinstance(schema, dict) else []
        GENERIC_WORDS = {"amount", "number", "date", "name", "total", "code", "type", "id", "no", "num"}
        used_label_indices: set = set()

        for sf in schema_fields:
            if isinstance(sf, dict):
                f_key = sf.get("key") or sf.get("name", "field")
                name_en = sf.get("name_en", "")
                name_ar = sf.get("name_ar", "")
                data_type = sf.get("data_type", "string")
            else:
                f_key = getattr(sf, "key", "field")
                name_en = getattr(sf, "name_en", "")
                name_ar = getattr(sf, "name_ar", "")
                data_type = getattr(sf, "data_type", "string")

            # Collect label search terms (require multi-word or non-generic word)
            raw_phrases = [t.lower().strip() for t in [f_key.replace("_", " "), name_en, name_ar] if t and len(t.strip()) >= 3]
            valid_terms = []
            for phrase in raw_phrases:
                words = phrase.split()
                if len(words) > 1:
                    valid_terms.append(phrase)
                elif len(words) == 1 and words[0] not in GENERIC_WORDS and len(words[0]) >= 3:
                    valid_terms.append(words[0])

            matched_label_idx: Optional[int] = None
            # Find candidate label token by checking multi-word phrase match
            for i, t in enumerate(tokens):
                if i in used_label_indices:
                    continue
                t_lower = t["text"].lower().strip(":")
                # Check single token contains full term
                found = False
                for term in valid_terms:
                    if term in t_lower:
                        matched_label_idx = i
                        found = True
                        break
                    # Also check 2-word phrase across adjacent tokens on same line
                    term_words = term.split()
                    if len(term_words) >= 2 and i + 1 < len(tokens) and (i + 1) not in used_label_indices:
                        t_next = tokens[i + 1]
                        if abs(t["center_y"] - t_next["center_y"]) < 0.03:
                            combined_2 = f"{t_lower} {t_next['text'].lower().strip(':')}"
                            if term in combined_2:
                                matched_label_idx = i
                                used_label_indices.add(i + 1)
                                found = True
                                break
                if found:
                    used_label_indices.add(i)
                    break

            matched_value_tokens: List[Dict[str, Any]] = []
            if matched_label_idx is not None:
                lbl = tokens[matched_label_idx]
                # Look for value tokens horizontally to the right
                cand_right = [
                    t for idx, t in enumerate(tokens)
                    if idx not in used_label_indices
                    and abs(t["center_y"] - lbl["center_y"]) < 0.035
                    and t["left"] >= lbl["right"] - 0.02
                ]
                if cand_right:
                    matched_value_tokens = cand_right[:8]
                else:
                    # Look for value tokens on the line directly below
                    cand_below = [
                        t for idx, t in enumerate(tokens)
                        if idx not in used_label_indices
                        and 0.005 < t["top"] - lbl["bottom"] < 0.06
                        and abs(t["center_x"] - lbl["center_x"]) < 0.35
                    ]
                    if cand_below:
                        matched_value_tokens = cand_below[:8]

            if matched_value_tokens:
                raw_val = " ".join(t["text"].strip(":") for t in matched_value_tokens).strip()
                val = raw_val

                if data_type == "date":
                    val = parse_date_string(normalize_arabic_digits(raw_val)) or raw_val
                elif data_type == "number":
                    cleaned = re.sub(r"[^\d\.\,]", "", normalize_arabic_digits(raw_val))
                    val = cleaned.replace(",", "") if cleaned else raw_val

                fields.append(ExtractedFieldData(
                    field_name=f_key,
                    value=val if val else None,
                    raw_value=raw_val if raw_val else None,
                    confidence=self._average_token_confidence(matched_value_tokens),
                    page_number=matched_value_tokens[0].get("page_number", 1),
                    bounding_box=self._union_token_boxes(matched_value_tokens)
                ))
            else:
                fields.append(ExtractedFieldData(
                    field_name=f_key,
                    value=None,
                    raw_value=None,
                    confidence=0.0,
                    page_number=1,
                    bounding_box=None
                ))

        return fields
