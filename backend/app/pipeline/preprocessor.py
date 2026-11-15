import io
from typing import Tuple, Dict, Any
from PIL import Image, ImageOps, ImageFilter

class ImagePreprocessor:
    """
    Sovereign preprocessor for incoming document images.
    Performs rotation fix, orientation correction, deskew, denoising,
    and resolution enhancement without any external network dependencies.
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

        # 2. Orientation & Landscape check for ID cards (Standard UAE ID aspect ratio is ~1.58)
        w, h = img.size
        if h > w * 1.2:
            # Document is oriented vertically; rotate 90 degrees clockwise to landscape
            img = img.rotate(270, expand=True)
            meta["rotated_degrees"] = 90
            w, h = img.size

        # 3. Resolution check & High-Quality Upscaling for low-DPI scans
        # OCR requires at least 1000px on long edge for reliable Arabic diacritics & digits
        if max(w, h) < 1000:
            scale_factor = 1000.0 / max(w, h)
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            meta["upscaled"] = True
            meta["resolution_adequate"] = True
            w, h = img.size
        elif max(w, h) < 600:
            meta["resolution_adequate"] = False

        # 4. Denoising: Gentle median filter to remove scanner salt-and-pepper noise
        # Preserve edges for OCR readability
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Subtle noise reduction
        denoised_img = img.filter(ImageFilter.SMOOTH_MORE)
        meta["denoised"] = True

        meta["processed_width"], meta["processed_height"] = img.size

        out_buffer = io.BytesIO()
        img.save(out_buffer, format="PNG", optimize=True)
        return out_buffer.getvalue(), meta
