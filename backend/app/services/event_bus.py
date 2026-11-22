import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, AsyncGenerator, Set

logger = logging.getLogger("event_bus")

class PipelineEventBus:
    """
    Sovereign In-Country Real-Time Event Bus.
    Dispatches pipeline stage events over Redis Pub/Sub with in-memory subscriber fan-out.
    Enforces strict tenant isolation: events never cross tenant boundaries.
    """
    def __init__(self):
        # In-memory subscriber queues: tenant_id -> set of asyncio.Queue
        self._tenant_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._doc_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._seen_event_ids: Set[str] = set()

    async def feed_external_event(self, event: Dict[str, Any]):
        """
        Feeds an external event from Redis subscriber into active SSE subscribers.
        Skips events previously seen/emitted locally to prevent duplication.
        """
        event_id = event.get("event_id")
        if event_id and event_id in self._seen_event_ids:
            return
        if event_id:
            self._seen_event_ids.add(event_id)
            if len(self._seen_event_ids) > 5000:
                self._seen_event_ids.clear()

        tenant_id = event.get("tenant_id")
        document_id = event.get("document_id")
        if not tenant_id:
            return

        async with self._lock:
            if tenant_id in self._tenant_subscribers:
                for q in list(self._tenant_subscribers[tenant_id]):
                    try:
                        q.put_nowait(event)
                    except asyncio.QueueFull:
                        pass

            if document_id:
                doc_key = f"{tenant_id}:{document_id}"
                if doc_key in self._doc_subscribers:
                    for q in list(self._doc_subscribers[doc_key]):
                        try:
                            q.put_nowait(event)
                        except asyncio.QueueFull:
                            pass

    async def emit_event(
        self,
        tenant_id: str,
        document_id: str,
        stage: str,
        status: str,
        stage_duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        progress_pct: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Emits an ordered pipeline event.
        Stages: queued, preprocessing, ocr, parsing, validating, needs_review, approved, failed.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        event = {
            "event_id": f"evt-{int(time.time()*1000)}-{document_id[:8]}",
            "document_id": document_id,
            "tenant_id": tenant_id,
            "stage": stage,
            "status": status,
            "stage_duration_ms": round(stage_duration_ms, 2) if stage_duration_ms is not None else None,
            "progress_pct": progress_pct,
            "details": details or {},
            "timestamp": now_utc
        }
        self._seen_event_ids.add(event["event_id"])

        # 1. Publish to Redis Pub/Sub if available
        try:
            from app.worker.queue import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                channel = f"tenant:{tenant_id}:events"
                redis_client.publish(channel, json.dumps(event))
        except Exception as e:
            logger.debug(f"Redis publish skipped or failed: {e}")

        # 2. Fan-out to active in-memory SSE subscribers
        async with self._lock:
            # Tenant-level subscribers
            if tenant_id in self._tenant_subscribers:
                for q in list(self._tenant_subscribers[tenant_id]):
                    try:
                        q.put_nowait(event)
                    except asyncio.QueueFull:
                        pass

            # Document-level subscribers
            doc_key = f"{tenant_id}:{document_id}"
            if doc_key in self._doc_subscribers:
                for q in list(self._doc_subscribers[doc_key]):
                    try:
                        q.put_nowait(event)
                    except asyncio.QueueFull:
                        pass

        logger.info(f"[RealTimeEvent] tenant={tenant_id} doc={document_id} stage={stage} status={status} duration={stage_duration_ms}ms")
        return event

    async def publish(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method accepting an event dictionary."""
        return await self.emit_event(
            tenant_id=event_data["tenant_id"],
            document_id=event_data.get("document_id", "system"),
            stage=event_data.get("stage", "info"),
            status=event_data.get("status", "processing"),
            stage_duration_ms=event_data.get("stage_duration_ms"),
            details=event_data.get("details"),
            progress_pct=event_data.get("progress_pct")
        )

    async def subscribe_tenant(self, tenant_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribes an authenticated client to real-time events strictly within their tenant."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if tenant_id not in self._tenant_subscribers:
                self._tenant_subscribers[tenant_id] = set()
            self._tenant_subscribers[tenant_id].add(queue)

        try:
            while True:
                # Wait for next event with keepalive heartbeat
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield event
                except asyncio.TimeoutError:
                    # Keepalive comment / ping
                    yield {
                        "type": "heartbeat",
                        "tenant_id": tenant_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
        finally:
            async with self._lock:
                if tenant_id in self._tenant_subscribers:
                    self._tenant_subscribers[tenant_id].discard(queue)
                    if not self._tenant_subscribers[tenant_id]:
                        del self._tenant_subscribers[tenant_id]

    async def subscribe_document(self, tenant_id: str, document_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribes an authenticated client to real-time events for a specific document."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        doc_key = f"{tenant_id}:{document_id}"
        async with self._lock:
            if doc_key not in self._doc_subscribers:
                self._doc_subscribers[doc_key] = set()
            self._doc_subscribers[doc_key].add(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield event
                    # If terminal stage, close stream after small grace window
                    if event.get("stage") in ["approved", "needs_review", "failed"]:
                        break
                except asyncio.TimeoutError:
                    yield {
                        "type": "heartbeat",
                        "tenant_id": tenant_id,
                        "document_id": document_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
        finally:
            async with self._lock:
                if doc_key in self._doc_subscribers:
                    self._doc_subscribers[doc_key].discard(queue)
                    if not self._doc_subscribers[doc_key]:
                        del self._doc_subscribers[doc_key]

event_bus = PipelineEventBus()
