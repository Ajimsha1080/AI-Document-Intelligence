import os
from typing import Optional
from fastapi import HTTPException, status
import filetype
from app.core.config import settings

# Strict allowed MIME types: PDF, JPG, PNG, TIFF only. SVG is strictly prohibited.
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
}

MIME_TO_EXTENSIONS = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/tiff": [".tif", ".tiff"],
}

def validate_magic_bytes(content: bytes, filename: Optional[str] = None) -> str:
    """
    Validates document content using magic bytes.
    Prevents file extension spoofing attacks (e.g., executable disguised as PDF/PNG).
    Enforces PDF, JPG, PNG, TIFF only. SVG is strictly prohibited.
    Returns verified MIME type or raises HTTPException.
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded. Content cannot be zero bytes."
        )

    # 1. Prohibit SVG explicitly
    if content.strip().startswith(b"<svg") or b"<svg" in content[:1024]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SVG files are not permitted for security reasons. Allowed formats: PDF, JPG, PNG, TIFF."
        )

    # 2. Check with filetype library
    kind = filetype.guess(content[:2048])
    mime = kind.mime if kind else None

    # 3. Fallback check for raw signatures
    if not mime:
        if content.startswith(b"%PDF"):
            mime = "application/pdf"
        elif content.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif content.startswith(b"II*\x00") or content.startswith(b"MM\x00*"):
            mime = "image/tiff"

    if not mime or mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported or invalid file format (detected: {mime or 'unknown'}). "
                f"Only verified PDF, JPG, PNG, and TIFF files are permitted."
            )
        )

    # 4. Check extension match to prevent extension spoofing
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        allowed_exts = MIME_TO_EXTENSIONS.get(mime, [])
        if ext and ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' does not match detected content type '{mime}'."
            )

    # 5. For PDFs, verify integrity and reject encrypted or malformed files
    if mime == "application/pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(content)
            # Check for encrypted PDF
            if hasattr(pdf, "is_encrypted") and pdf.is_encrypted():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Encrypted or password-protected PDF files cannot be processed. Please provide an unencrypted document."
                )
            if len(pdf) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malformed or empty PDF file. No pages found."
                )
        except HTTPException:
            raise
        except Exception as e:
            err_msg = str(e).lower()
            if "password" in err_msg or "encrypt" in err_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Encrypted or password-protected PDF files cannot be processed. Please provide an unencrypted document."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed or unreadable PDF document: {e}"
            )

    return mime

def validate_file_size(content_length: int) -> None:
    """Validates that file content does not exceed configured size ceiling."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if content_length > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum permissible size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )
