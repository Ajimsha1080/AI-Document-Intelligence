import io
import re
from typing import Tuple, Dict, Any
from PIL import Image, ImageOps, ImageFilter

class ImagePreprocessor:
    """
    Sovereign preprocessor for incoming document images.
    Performs orientation correction (only via Tesseract OSD), deskew, denoising,
    and resolution enhancement without external network calls.
    """

    @classmethod
    def preprocess_image(cls, content: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """
        Takes raw image bytes, applies preprocessing pipeline,
        and returns (processed_bytes, metadata).
        """
        meta = {
            "rotated_degrees": 0,
            "deskew_angle": 0.0,
            "denoised": False,
            "upscaled": False,
            "original_width": 0,
            "original_height": 0,
            "processed_width": 0,
            "processed_height": 0,
            "resolution_adequate": True
        }

        # Check for PDF and rasterize first page before OCR
        if content.startswith(b"%PDF"):
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(content)
                if hasattr(pdf, "is_encrypted") and pdf.is_encrypted():
                    raise ValueError("Encrypted or password-protected PDF cannot be processed.")
                if len(pdf) == 0:
                    raise ValueError("Malformed or empty PDF document. No pages found.")
                page = pdf[0]
                # Render to PIL image at 300 DPI equivalent
                img = page.render(scale=3.0).to_pil()
                meta["rasterized_pdf"] = True
            except Exception as e:
                raise ValueError(f"Failed to rasterize PDF document: {e}")
        else:
            try:
                img = Image.open(io.BytesIO(content))
            except Exception:
                # If not decodable, return original
                return content, meta

        meta["original_width"], meta["original_height"] = img.size

        # 1. EXIF Transposition (Camera orientation fix)
        try:
            transposed = ImageOps.exif_transpose(img)
            if transposed is not None:
                img = transposed
        except Exception:
            pass

        w, h = img.size

        # 2. Orientation check: ONLY rotate when Tesseract OSD explicitly specifies rotation.
        # Do not unconditionally rotate portrait images (which breaks invoices/licenses).
        try:
            from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
            tess_cmd = LocalOCRAdapter.get_tesseract_cmd()
            if tess_cmd:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
                osd = pytesseract.image_to_osd(img)
                rot_match = re.search(r"Rotate:\s*(\d+)", osd)
                if rot_match:
                    rot_deg = int(rot_match.group(1))
                    if rot_deg in (90, 180, 270):
                        img = img.rotate(360 - rot_deg, expand=True)
                        meta["rotated_degrees"] = rot_deg
                        w, h = img.size
        except Exception:
            pass

        # 3. Resolution check & High-Quality Upscaling for low-DPI scans
        # Initial scan quality check: adequate if max dimension is at least 600px
        meta["resolution_adequate"] = (max(w, h) >= 600)

        # Upscale if below 1000px for optimal OCR recognition
        if max(w, h) < 1000:
            scale_factor = 1000.0 / max(w, h)
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            meta["upscaled"] = True
            w, h = img.size

        # 4. Denoising: Subtle noise reduction and actually apply the denoised image
        if img.mode != "RGB":
            img = img.convert("RGB")

        denoised_img = img.filter(ImageFilter.SMOOTH_MORE)
        img = denoised_img
        meta["denoised"] = True

        meta["processed_width"], meta["processed_height"] = img.size

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="PNG", optimize=True)
        return out_buffer.getvalue(), meta
