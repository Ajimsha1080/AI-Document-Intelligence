import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_actor, AuthenticatedActor
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["Sovereign RAG"])

@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    payload: RAGQueryRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """
    Sovereign In-Country RAG Endpoint.
    Hybrid retrieval (pgvector + full-text RRF), layout citations,
    and prompt injection guard. Guaranteed 0 cross-border data egress.
    """
    res = await rag_service.answer_question(
        db=db,
        tenant_id=actor.tenant_id,
        query=payload.query,
        document_id=payload.document_id,
        top_k=payload.top_k
    )
    return res

@router.get("/stream")
async def stream_rag_answer(
    query: str = Query(..., min_length=1),
    document_id: Optional[str] = Query(None),
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """
    Server-Sent Events (SSE) Streaming RAG response with live tokens and citations.
    """
    res = await rag_service.answer_question(
        db=db,
        tenant_id=actor.tenant_id,
        query=query,
        document_id=document_id,
        top_k=5
    )

    async def event_generator():
        # Stream metadata first
        yield f"event: metadata\ndata: {json.dumps({'mode': res['mode'], 'citations': res['citations'], 'confidence': res['confidence']})}\n\n"
        await asyncio.sleep(0.01)

        # Stream words as real-time tokens
        words = res["answer"].split()
        for i, word in enumerate(words):
            yield f"event: token\ndata: {json.dumps({'token': word + ' ', 'index': i})}\n\n"
            await asyncio.sleep(0.01)

        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
