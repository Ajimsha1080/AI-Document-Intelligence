import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import Permission
from app.core.security import mask_pii_text
from app.api.deps import require_permission, require_stream_permission, AuthenticatedActor
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag.rag_service import rag_service
from app.services.rag.prompt_guard import check_prompt_injection
from app.services.rag.query_router import route_and_lookup_structured_field

router = APIRouter(prefix="/rag", tags=["Sovereign RAG"])

@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    payload: RAGQueryRequest,
    actor: AuthenticatedActor = Depends(require_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """
    Sovereign In-Country RAG Endpoint.
    Hybrid retrieval (pgvector + full-text RRF), layout citations,
    and prompt injection guard. Guaranteed 0 cross-border data egress.
    Masks PII in answers for non-admin actors.
    """
    res = await rag_service.answer_question(
        db=db,
        tenant_id=actor.tenant_id,
        query=payload.query,
        document_id=payload.document_id,
        top_k=payload.top_k
    )

    if actor.role != "admin":
        if "answer" in res and res["answer"]:
            res["answer"] = mask_pii_text(res["answer"])
        if "answer_ar" in res and res["answer_ar"]:
            res["answer_ar"] = mask_pii_text(res["answer_ar"])
        if "citations" in res:
            for cit in res["citations"]:
                if isinstance(cit, dict) and "snippet" in cit:
                    cit["snippet"] = mask_pii_text(cit["snippet"])

    return res

@router.get("/stream")
async def stream_rag_answer(
    query: str = Query(..., min_length=1),
    document_id: Optional[str] = Query(None),
    actor: AuthenticatedActor = Depends(require_stream_permission(Permission.DOCUMENT_VIEW)),
    db: AsyncSession = Depends(get_db)
):
    """
    Server-Sent Events (SSE) Streaming RAG response.
    Streams real Ollama tokens when local LLM is available;
    stops calling it real-time and serves grounded synthesis if falling back.
    Masks PII in answers for non-admin actors.
    """
    # 1. Prompt Injection Guard
    is_suspicious, reason = check_prompt_injection(query)
    if is_suspicious:
        async def refusal_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Request refused', 'detail': reason, 'real_time': False})}\n\n"
        return StreamingResponse(
            refusal_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    # 2. Structured Field Lookup
    is_structured, structured_res = await route_and_lookup_structured_field(
        db=db,
        tenant_id=actor.tenant_id,
        query=query,
        document_id=document_id
    )
    if is_structured and structured_res:
        ans = structured_res["answer"]
        if actor.role != "admin":
            ans = mask_pii_text(ans)
        async def structured_stream():
            yield f"event: metadata\ndata: {json.dumps({'mode': 'structured_field', 'citations': structured_res['citations'], 'confidence': structured_res['confidence'], 'real_time': False})}\n\n"
            yield f"event: token\ndata: {json.dumps({'token': ans, 'real_time': False})}\n\n"
            yield f"event: message\ndata: {json.dumps({'answer': ans, 'real_time': False})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
        return StreamingResponse(
            structured_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    # 3. Hybrid Retrieval
    retrieved_chunks = await rag_service.retriever.retrieve(
        db=db,
        tenant_id=actor.tenant_id,
        query=query,
        document_id=document_id,
        top_k=5
    )
    clean_chunks = []
    for c in retrieved_chunks:
        c_text = c.get("chunk_text") or c.get("snippet") or ""
        is_inj, _ = check_prompt_injection(c_text)
        if not is_inj:
            clean_chunks.append(c)
    retrieved_chunks = clean_chunks

    if not retrieved_chunks:
        async def not_found_stream():
            yield f"event: metadata\ndata: {json.dumps({'mode': 'hybrid_rag', 'citations': [], 'confidence': 0.0, 'real_time': False})}\n\n"
            yield f"event: token\ndata: {json.dumps({'token': 'Not found in your documents.', 'real_time': False})}\n\n"
            yield f"event: message\ndata: {json.dumps({'answer': 'Not found in your documents.', 'real_time': False})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
        return StreamingResponse(
            not_found_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    # 4. Stream real Ollama tokens or deliver fallback without claiming real-time
    async def sse_event_generator():
        valid_chunk_ids = {c["id"] for c in retrieved_chunks}
        citations = []
        for c in retrieved_chunks[:3]:
            if c.get("id") in valid_chunk_ids:
                snippet = c.get("chunk_text", "")[:150]
                if actor.role != "admin":
                    snippet = mask_pii_text(snippet)
                citations.append({
                    "chunk_id": c["id"],
                    "document_id": c.get("document_id"),
                    "page": c.get("page_number", 1),
                    "bounding_box": c.get("bounding_box"),
                    "snippet": snippet
                })

        generator = rag_service.generator
        if hasattr(generator, "stream_generate"):
            stream_gen = generator.stream_generate(query, retrieved_chunks)
            first_item = None
            try:
                first_item = await stream_gen.__anext__()
            except StopAsyncIteration:
                pass

            is_real_time = first_item.get("real_time", False) if first_item else False
            yield f"event: metadata\ndata: {json.dumps({'mode': 'hybrid_rag', 'citations': citations, 'real_time': is_real_time})}\n\n"

            if first_item:
                tok = first_item.get("token", "")
                if actor.role != "admin":
                    tok = mask_pii_text(tok)
                if is_real_time:
                    yield f"event: token\ndata: {json.dumps({'token': tok})}\n\n"
                else:
                    yield f"event: message\ndata: {json.dumps({'answer': tok, 'real_time': False})}\n\n"

                if not first_item.get("done", False):
                    async for item in stream_gen:
                        tok = item.get("token", "")
                        if actor.role != "admin":
                            tok = mask_pii_text(tok)
                        if is_real_time:
                            yield f"event: token\ndata: {json.dumps({'token': tok})}\n\n"
                        else:
                            yield f"event: message\ndata: {json.dumps({'answer': tok, 'real_time': False})}\n\n"
        else:
            res = generator.generate(query, retrieved_chunks)
            ans = res.get("answer", "")
            if actor.role != "admin":
                ans = mask_pii_text(ans)
            yield f"event: metadata\ndata: {json.dumps({'mode': 'hybrid_rag', 'citations': citations, 'real_time': False})}\n\n"
            yield f"event: message\ndata: {json.dumps({'answer': ans, 'real_time': False})}\n\n"

        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
