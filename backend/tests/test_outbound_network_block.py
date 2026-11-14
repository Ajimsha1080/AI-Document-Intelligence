import io
import socket
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.preprocessor import ImagePreprocessor
from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
from app.worker.tasks import process_document_pipeline

SYNTHETIC_SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="630">
  <rect width="1000" height="630" fill="#f0f4f8"/>
  <text x="250" y="80">UNITED ARAB EMIRATES FEDERAL AUTHORITY FOR IDENTITY</text>
  <text x="250" y="120">بطاقة الهوية الإماراتية Identity Card</text>
  <text x="250" y="200">الاسم: سالم راشد سيف الشامسي</text>
  <text x="250" y="260">Name: SALEM RASHED SAIF ALSHAMSI</text>
  <text x="250" y="340">Identity Number / رقم الهوية: 784-1988-1234567-1</text>
  <text x="250" y="420">Nationality / الجنسية: United Arab Emirates</text>
  <text x="250" y="480">Date of Birth / تاريخ الميلاد: 15/04/1988</text>
  <text x="600" y="480">Expiry Date / تاريخ الانتهاء: 30/12/2028</text>
  <text x="250" y="540">Sex / الجنس: M</text>
</svg>""".encode("utf-8")

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
    files = {"file": ("airgap_test_eid.svg", io.BytesIO(SYNTHETIC_SVG_CONTENT), "image/png")}
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
    assert processed_doc.confidence_score >= 0.85

    # 3. Direct Adapter Verification
    adapter = LocalOCRAdapter()
    result = await adapter.extract_fields(
        document_bytes=SYNTHETIC_SVG_CONTENT,
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
