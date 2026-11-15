import io
import socket
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.preprocessor import ImagePreprocessor
from PIL import Image
from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
from app.worker.tasks import process_document_pipeline

def _create_test_png():
    buf = io.BytesIO()
    img = Image.new("RGB", (1000, 630), color=(240, 244, 248))
    img.save(buf, format="PNG")
    return buf.getvalue()

SYNTHETIC_PNG_CONTENT = _create_test_png()

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1", "test"}

class OutboundNetworkViolationError(Exception):
    pass

@pytest.fixture
def strict_network_blocker(monkeypatch):
    """
    Sovereignty Network Blocker Fixture:
    Intercepts socket.socket.connect and socket.getaddrinfo.
    Immediately raises OutboundNetworkViolationError if any remote non-loopback host is contacted.
    """
    orig_connect = socket.socket.connect
    orig_getaddrinfo = socket.getaddrinfo

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, (tuple, list)) else address
        if host not in ALLOWED_HOSTS and not str(host).startswith("127."):
            raise OutboundNetworkViolationError(
                f"Sovereign Security Breach: Outbound connection attempted to remote destination '{address}'"
            )
        return orig_connect(self, address)

    def guarded_getaddrinfo(host, port, *args, **kwargs):
        if host not in ALLOWED_HOSTS and not str(host).startswith("127."):
            raise OutboundNetworkViolationError(
                f"Sovereign Security Breach: Remote DNS lookup attempted for host '{host}'"
            )
        return orig_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    yield

@pytest.mark.asyncio
async def test_zero_outbound_network_calls_during_pipeline_processing(
    strict_network_blocker,
    async_client: AsyncClient,
    seeded_data: dict,
    db_session: AsyncSession
):
    """
    Step 7 Test: Asserts that processing a document through preprocessing, local OCR,
    parsing, checksum calculation, and validation makes exactly ZERO outbound network calls.
    """
    token = seeded_data["admin_token"]
    tenant = seeded_data["tenant_1"]

    # 1. Upload Document
    files = {"file": ("airgap_test_eid.png", io.BytesIO(SYNTHETIC_PNG_CONTENT), "image/png")}
    up = await async_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"document_type_code": "emirates_id"}
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # 2. Run Pipeline Worker Task (Guarded by strict_network_blocker)
    processed_doc = await process_document_pipeline(doc_id, tenant.id, db=db_session)

    assert processed_doc is not None
    assert processed_doc.status in ["approved", "needs_review"]
    assert processed_doc.confidence_score is not None

    # 3. Direct Adapter Verification
    adapter = LocalOCRAdapter()
    result = await adapter.extract_fields(
        document_bytes=SYNTHETIC_PNG_CONTENT,
        document_type_code="emirates_id",
        schema_definition={}
    )
    assert result.backend_used == "local"
    assert len(result.fields) >= 7

def test_network_blocker_detects_and_fails_on_remote_egress(strict_network_blocker):
    """
    Step 7 Test: Verifies that the guard reliably catches and fails if any third-party
    telemetry or cloud OCR endpoint is contacted.
    """
    with pytest.raises(OutboundNetworkViolationError) as exc_info:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("api.openai.com", 443))

    assert "Sovereign Security Breach" in str(exc_info.value)
