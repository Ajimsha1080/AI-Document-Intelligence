from typing import List, Dict, Any, Optional
from app.services.rag.arabic_normalizer import normalize_arabic_text

def _get_coord(b: Any, key: str, default: float = 0.0) -> float:
    if isinstance(b, dict):
        return b.get(key, default)
    return getattr(b, key, default)

def build_bounding_box_union(boxes: List[Any], page: int = 1) -> Optional[Dict[str, Any]]:
    """Computes normalized union bounding box from token boxes."""
    if not boxes:
        return None
    min_x = min(_get_coord(b, "x", 0.0) for b in boxes)
    min_y = min(_get_coord(b, "y", 0.0) for b in boxes)
    max_r = max(_get_coord(b, "x", 0.0) + _get_coord(b, "width", 0.0) for b in boxes)
    max_b = max(_get_coord(b, "y", 0.0) + _get_coord(b, "height", 0.0) for b in boxes)

    return {
        "x": round(max(0.0, min_x), 4),
        "y": round(max(0.0, min_y), 4),
        "width": round(max(0.01, min(1.0 - min_x, max_r - min_x)), 4),
        "height": round(max(0.01, min(1.0 - min_y, max_b - min_y)), 4),
        "page": page
    }

def chunk_document_tokens(
    tokens: List[Dict[str, Any]],
    target_chunk_tokens: int = 60,
    page_number: int = 1
) -> List[Dict[str, Any]]:
    """
    Layout-aware chunking from real OCR token sequences.
    Groups sequential tokens into coherent chunks while tracking token boxes
    and generating the union bounding box for every chunk.
    """
    if not tokens:
        return []

    chunks: List[Dict[str, Any]] = []
    current_tokens: List[str] = []
    current_boxes: List[Dict[str, float]] = []
    chunk_index = 0

    for token in tokens:
        text = token.get("text", "").strip()
        if not text:
            continue

        box = token.get("box") or {}
        current_tokens.append(text)
        if box:
            current_boxes.append(box)

        if len(current_tokens) >= target_chunk_tokens:
            chunk_text = " ".join(current_tokens)
            chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_number,
                "chunk_text": chunk_text,
                "chunk_text_normalized": normalize_arabic_text(chunk_text),
                "bounding_box": build_bounding_box_union(current_boxes, page=page_number),
                "token_count": len(current_tokens)
            })
            chunk_index += 1
            current_tokens = []
            current_boxes = []

    # Final residual chunk
    if current_tokens:
        chunk_text = " ".join(current_tokens)
        chunks.append({
            "chunk_index": chunk_index,
            "page_number": page_number,
            "chunk_text": chunk_text,
            "chunk_text_normalized": normalize_arabic_text(chunk_text),
            "bounding_box": build_bounding_box_union(current_boxes, page=page_number),
            "token_count": len(current_tokens)
        })

    return chunks

def chunk_text_fallback(
    raw_text: str,
    target_words: int = 50,
    page_number: int = 1
) -> List[Dict[str, Any]]:
    """
    Fallback layout chunker when token positions are unavailable.
    Generates sensible page-spanning layout chunks.
    """
    if not raw_text or not raw_text.strip():
        return []

    words = raw_text.strip().split()
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for i in range(0, len(words), target_words):
        slice_words = words[i:i + target_words]
        chunk_text = " ".join(slice_words)
        # Approximate vertical position down page
        y_pos = min(0.9, 0.05 + (chunk_index * 0.15))
        chunks.append({
            "chunk_index": chunk_index,
            "page_number": page_number,
            "chunk_text": chunk_text,
            "chunk_text_normalized": normalize_arabic_text(chunk_text),
            "bounding_box": {
                "x": 0.05,
                "y": round(y_pos, 4),
                "width": 0.90,
                "height": 0.12,
                "page": page_number
            },
            "token_count": len(slice_words)
        })
        chunk_index += 1

    return chunks
