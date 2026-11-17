import math
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.document_chunk import DocumentChunk
from app.services.rag.arabic_normalizer import normalize_arabic_text
from app.services.rag.providers import (
    EmbeddingProvider,
    RerankerProvider,
    LocalHashingSemanticEmbedding,
    LocalCrossEncoderReranker,
    get_default_embedding_provider
)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    return dot / (norm1 * norm2)

class HybridRetriever:
    """
    Hybrid Retriever combining Vector Search and Lexical/Text Matching
    fused with Reciprocal Rank Fusion (RRF) and Multilingual Reranking.
    Enforces strict tenant isolation on every database query.
    """
    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None
    ):
        self.embedder = embedding_provider or get_default_embedding_provider()
        self.reranker = reranker_provider or LocalCrossEncoderReranker()

    async def retrieve(
        self,
        db: AsyncSession,
        tenant_id: str,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        # 1. Enforce strict tenant boundary in base query
        stmt = select(DocumentChunk).where(DocumentChunk.tenant_id == tenant_id)
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # 2. Vector scoring with dimensional auto-adaptation
        sample_emb = chunks[0].embedding if chunks and chunks[0].embedding else None
        sample_dim = len(sample_emb) if sample_emb else None
        if sample_dim and sample_dim == 128 and getattr(self.embedder, "dim", 384) != 128:
            query_vec = LocalHashingSemanticEmbedding(dim=128).embed_query(query)
        else:
            query_vec = self.embedder.embed_query(query)

        vector_candidates = []
        for ch in chunks:
            sim = cosine_similarity(query_vec, ch.embedding or [])
            vector_candidates.append((ch, sim))

        # Rank by vector similarity descending
        vector_candidates.sort(key=lambda x: x[1], reverse=True)

        # 3. Lexical / Full-Text scoring
        norm_query = normalize_arabic_text(query)
        query_words = set(norm_query.split())
        text_candidates = []

        for ch in chunks:
            norm_chunk = ch.chunk_text_normalized or normalize_arabic_text(ch.chunk_text)
            chunk_words = set(norm_chunk.split())
            overlap = len(query_words.intersection(chunk_words))
            lex_score = overlap / max(1, len(query_words))
            if norm_query in norm_chunk:
                lex_score += 0.5
            text_candidates.append((ch, lex_score))

        # Rank by lexical score descending
        text_candidates.sort(key=lambda x: x[1], reverse=True)

        # 4. Reciprocal Rank Fusion (RRF) with constant k=60
        K = 60
        rrf_map: Dict[str, Dict[str, Any]] = {}

        for rank, (ch, score) in enumerate(vector_candidates, start=1):
            if ch.id not in rrf_map:
                rrf_map[ch.id] = {
                    "id": ch.id,
                    "document_id": ch.document_id,
                    "page_number": ch.page_number,
                    "chunk_text": ch.chunk_text,
                    "chunk_text_normalized": ch.chunk_text_normalized,
                    "bounding_box": ch.bounding_box,
                    "vector_score": score,
                    "lexical_score": 0.0,
                    "rrf_score": 0.0
                }
            rrf_map[ch.id]["rrf_score"] += 1.0 / (K + rank)

        for rank, (ch, score) in enumerate(text_candidates, start=1):
            if ch.id not in rrf_map:
                rrf_map[ch.id] = {
                    "id": ch.id,
                    "document_id": ch.document_id,
                    "page_number": ch.page_number,
                    "chunk_text": ch.chunk_text,
                    "chunk_text_normalized": ch.chunk_text_normalized,
                    "bounding_box": ch.bounding_box,
                    "vector_score": 0.0,
                    "lexical_score": score,
                    "rrf_score": 0.0
                }
            rrf_map[ch.id]["lexical_score"] = score
            rrf_map[ch.id]["rrf_score"] += 1.0 / (K + rank)

        fused_candidates = list(rrf_map.values())
        fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)

        # 5. Multilingual Cross-Encoder Reranker
        reranked = self.reranker.rerank(query, fused_candidates[: top_k * 2])
        return reranked[:top_k]
