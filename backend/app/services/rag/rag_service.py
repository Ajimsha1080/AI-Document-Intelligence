import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.prompt_guard import check_prompt_injection, sanitize_untrusted_text
from app.services.rag.query_router import route_and_lookup_structured_field
from app.services.rag.retriever import HybridRetriever
from app.services.rag.providers import get_default_generator_provider, SovereignLocalGenerator

logger = logging.getLogger("rag_service")

class SovereignRAGService:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.generator = get_default_generator_provider(threshold=0.20)

    async def answer_question(
        self,
        db: AsyncSession,
        tenant_id: str,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Executes Sovereign In-Country RAG Q&A:
        1. Checks for prompt injection & adversarial payloads.
        2. Routes structured vs unstructured queries.
        3. Retrieves hybrid vectors + full-text RRF with tenant boundary.
        4. Synthesizes answers and strictly verifies citations.
        """
        # 1. Guard against prompt injection - refuse immediately if flagged
        is_suspicious, reason = check_prompt_injection(query)
        if is_suspicious:
            logger.warning(f"Sovereign Prompt Guard refused query: {reason}")
            return {
                "query": query,
                "answer": "Request refused: Detected prompt injection pattern or policy violation.",
                "answer_ar": "تم رفض الطلب: تم اكتشاف محاولة حقن أو انتهاك لسياسة الأمان.",
                "mode": "refusal",
                "confidence": 0.0,
                "citations": [],
                "prompt_guard_flagged": True
            }

        clean_query = sanitize_untrusted_text(query)

        # 2. Check structured field router first
        is_structured, structured_res = await route_and_lookup_structured_field(
            db=db,
            tenant_id=tenant_id,
            query=clean_query,
            document_id=document_id
        )

        if is_structured and structured_res:
            return {
                "query": query,
                "answer": structured_res["answer"],
                "answer_ar": structured_res["answer_ar"],
                "mode": "structured_field",
                "confidence": structured_res["confidence"],
                "citations": structured_res["citations"],
                "prompt_guard_flagged": is_suspicious
            }

        # 3. Hybrid Retrieval (Vector + Full-Text RRF)
        retrieved_chunks = await self.retriever.retrieve(
            db=db,
            tenant_id=tenant_id,
            query=clean_query,
            document_id=document_id,
            top_k=top_k
        )

        # Drop retrieved chunks containing injection text
        clean_retrieved = []
        for c in retrieved_chunks:
            c_text = c.get("chunk_text") or c.get("snippet") or ""
            c_inj, _ = check_prompt_injection(c_text)
            if not c_inj:
                clean_retrieved.append(c)
        retrieved_chunks = clean_retrieved

        if not retrieved_chunks:
            return {
                "query": query,
                "answer": "Not found in your documents.",
                "answer_ar": "غير موجود في مستنداتك.",
                "mode": "hybrid_rag",
                "confidence": 0.0,
                "citations": [],
                "prompt_guard_flagged": False
            }

        # 4. Generate grounded answer
        if hasattr(self.generator, "generate_async"):
            gen_res = await self.generator.generate_async(clean_query, retrieved_chunks)
        else:
            gen_res = self.generator.generate(clean_query, retrieved_chunks)

        # 5. Strict citation verification: every citation must exist in retrieved chunks
        valid_chunk_ids = {c["id"] for c in retrieved_chunks}
        verified_citations = [
            c for c in gen_res.get("citations", [])
            if c.get("chunk_id") in valid_chunk_ids
        ]

        return {
            "query": query,
            "answer": gen_res["answer"],
            "answer_ar": gen_res.get("answer_ar", ""),
            "mode": "hybrid_rag",
            "confidence": gen_res.get("confidence", 0.0),
            "citations": verified_citations,
            "prompt_guard_flagged": is_suspicious
        }

rag_service = SovereignRAGService()
