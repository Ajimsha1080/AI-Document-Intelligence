import io
import json
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from PIL import Image

from app.models.document import Document
from app.services.event_bus import event_bus
from app.worker.tasks import _run_pipeline_core
from tests.mock_adapter import MockModelAdapter


def _create_test_image_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_event_bus_isolated_by_tenant():
    """Verify that subscriber for tenant_b never receives events published for tenant_a."""
    tenant_a = "tenant-a-uuid"
    tenant_b = "tenant-b-uuid"

    received_a = []
    received_b = []

    async def listen_a():
        async for evt in event_bus.subscribe_tenant(tenant_a):
            received_a.append(evt)
            if evt.get("stage") == "done":
                break

    async def listen_b():
        async for evt in event_bus.subscribe_tenant(tenant_b):
            received_b.append(evt)
            if evt.get("stage") == "done":
                break

    task_a = asyncio.create_task(listen_a())
    task_b = asyncio.create_task(listen_b())

    # Small sleep to allow subscriptions to register
    await asyncio.sleep(0.05)

    # Publish events to tenant_a
    await event_bus.publish({
        "tenant_id": tenant_a,
        "document_id": "doc-1",
        "stage": "preprocessing",
        "status": "processing",
        "stage_duration_ms": 12.5
    })
    await event_bus.publish({
        "tenant_id": tenant_a,
        "document_id": "doc-1",
        "stage": "done",
        "status": "completed",
        "stage_duration_ms": 45.2
    })

    # Publish separate event to tenant_b
    await event_bus.publish({
        "tenant_id": tenant_b,
        "document_id": "doc-2",
        "stage": "done",
        "status": "completed",
        "stage_duration_ms": 10.0
    })

    await asyncio.gather(task_a, task_b)

    # Tenant A received only tenant_a events
    assert len(received_a) == 2
    assert all(e["tenant_id"] == tenant_a for e in received_a)
    assert received_a[0]["stage"] == "preprocessing"
    assert received_a[1]["stage"] == "done"

    # Tenant B received only tenant_b events
    assert len(received_b) == 1
    assert received_b[0]["tenant_id"] == tenant_b
    assert received_b[0]["document_id"] == "doc-2"


@pytest.mark.asyncio
async def test_pipeline_emits_ordered_events_with_durations(db_session, seeded_data: dict):
    """
    Verify that running the pipeline on a document emits the ordered sequence:
    preprocessing -> ocr -> parsing -> validating -> terminal (needs_review or approved),
    all containing real stage_duration_ms.
    """
    from app.services.storage_service import storage_service

    tenant = seeded_data["tenant_1"]
    img_bytes = _create_test_image_bytes()
    doc_id = "test-doc-evt-001"
    storage_path = storage_service.upload_document_file(
        tenant_id=tenant.id,
        document_id=doc_id,
        filename="test_card.png",
        content=img_bytes,
        mime_type="image/png"
    )

    doc = Document(
        id=doc_id,
        tenant_id=tenant.id,
        file_name="test_card.png",
        storage_path=storage_path,
        file_size=len(img_bytes),
        mime_type="image/png",
        status="queued",
        document_type_id=None
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    captured_events = []

    async def capture_events():
        async for evt in event_bus.subscribe_document(tenant.id, doc.id):
            captured_events.append(evt)
            if evt.get("stage") in ("needs_review", "approved", "failed"):
                break

    listener = asyncio.create_task(capture_events())
    await asyncio.sleep(0.05)

    # Execute pipeline core
    await _run_pipeline_core(
        document_id=doc.id,
        tenant_id=tenant.id,
        db=db_session
    )

    await asyncio.wait_for(listener, timeout=5.0)

    stages = [e["stage"] for e in captured_events]
    assert stages == ["preprocessing", "ocr", "parsing", "validating", "needs_review"]

    for evt in captured_events:
        assert "stage_duration_ms" in evt
        assert isinstance(evt["stage_duration_ms"], (int, float))
        assert evt["stage_duration_ms"] >= 0
        assert evt["tenant_id"] == tenant.id
        assert evt["document_id"] == doc.id


@pytest.mark.asyncio
async def test_sse_endpoint_cross_tenant_isolation(async_client: AsyncClient, seeded_data: dict):
    """
    Assert that a user from Tenant B cannot access or stream events for a document belonging to Tenant A.
    """
    token_b = seeded_data["tenant2_token"]
    tenant_a = seeded_data["tenant_1"]

    # Post doc as tenant A
    token_a = seeded_data["admin_token"]
    file_bytes = _create_test_image_bytes()
    files = {"file": ("isolated.png", io.BytesIO(file_bytes), "image/png")}
    data = {"document_type_code": "emirates_id"}

    upload_resp = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files=files,
        data=data
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Tenant B tries to connect to Tenant A's document event stream -> Must 404
    resp_b = await async_client.get(
        f"/api/v1/documents/{doc_id}/events",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_b.status_code == 404
