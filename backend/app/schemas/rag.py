from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)

class RAGCitation(BaseModel):
    chunk_id: str
    document_id: Optional[str] = None
    page: int = 1
    bounding_box: Optional[Dict[str, Any]] = None
    snippet: str

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    answer_ar: str
    mode: str
    confidence: float
    citations: List[RAGCitation]
    prompt_guard_flagged: bool = False
