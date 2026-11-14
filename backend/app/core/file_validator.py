from typing import Tuple
from fastapi import HTTPException, status
import filetype
from app.core.config import settings

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "image/svg+xml": ".svg",
}

def validate_magic_bytes(content: bytes) -> str:
    """
    Validates document content using magic bytes.
    Prevents file extension spoofing attacks (e.g., executable disguised as PDF/PNG).
    Returns verified MIME type or raises HTTPException.
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded. Content cannot be zero bytes."
        )

    # 1. Check with filetype library
    kind = filetype.guess(content[:2048])
    mime = kind.mime if kind else None

    # 2. Fallback check for raw signatures
    if not mime:
        if content.startswith(b"%PDF"):
            mime = "application/pdf"
        elif content.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif content.startswith(b"II*\x00") or content.startswith(b"MM\x00*"):
            mime = "image/tiff"
        elif content.strip().startswith(b"<svg") or b"<svg" in content[:256]:
            mime = "image/svg+xml"

    if not mime or mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported or invalid file format (detected: {mime or 'unknown'}). "
                f"Only verified PDF, JPG, PNG, and TIFF files are permitted."
            )
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
