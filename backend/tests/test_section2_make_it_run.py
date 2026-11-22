import os
import sys
import tempfile
import asyncio
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.core.database import Base
from app.core.seed import seed_defaults
from app.worker.queue import get_redis_client, get_worker_redis_client
from app.services.event_bus import event_bus


def test_alembic_upgrade_head_creates_all_model_tables():
    """Verify that 'alembic upgrade head' creates every model table including document_chunks."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        tmp_db_path = tmp_db.name

    try:
        sqlite_async_url = f"sqlite+aiosqlite:///{tmp_db_path.replace('\\', '/')}"
        sqlite_sync_url = f"sqlite:///{tmp_db_path.replace('\\', '/')}"
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_async_url)

        # Run migration to head
        command.upgrade(alembic_cfg, "head")

        # Inspect tables in newly created DB
        engine = create_engine(sqlite_sync_url)
        inspector = inspect(engine)
        created_tables = set(inspector.get_table_names())

        expected_model_tables = set(Base.metadata.tables.keys())
        # Assert every model table was created
        for table in expected_model_tables:
            assert table in created_tables, f"Table '{table}' was not created by alembic upgrade head"

        # Explicitly verify document_chunks columns
        columns = {col["name"] for col in inspector.get_columns("document_chunks")}
        assert "id" in columns
        assert "tenant_id" in columns
        assert "document_id" in columns
        assert "page_number" in columns
        assert "chunk_index" in columns
        assert "chunk_text" in columns
        assert "chunk_text_normalized" in columns
        assert "token_count" in columns
        assert "created_at" in columns
        engine.dispose()
    finally:
        try:
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_idempotent_seed_creates_tenant_admin_and_three_doc_types(db_session):
    """Verify seed_defaults creates tenant, admin, and 3 doc types and is idempotent."""
    # Run first time
    res1 = await seed_defaults(db_session)
    assert res1["seeded"] is True
    assert res1["admin_email"] == settings.DEFAULT_ADMIN_EMAIL.strip().lower()

    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.document_type import DocumentType

    tenant = (await db_session.execute(select(Tenant).where(Tenant.id == settings.DEFAULT_TENANT_ID))).scalar_one_or_none()
    assert tenant is not None
    assert tenant.id == settings.DEFAULT_TENANT_ID

    admin = (await db_session.execute(select(User).where(User.email == settings.DEFAULT_ADMIN_EMAIL.strip().lower()))).scalar_one_or_none()
    assert admin is not None
    assert admin.role == "admin"
    assert admin.tenant_id == tenant.id

    doc_types = (await db_session.execute(select(DocumentType).where(DocumentType.tenant_id == tenant.id))).scalars().all()
    codes = {dt.code for dt in doc_types}
    assert "emirates_id" in codes
    assert "uae_trade_license" in codes
    assert "commercial_invoice" in codes

    # Run second time: must be idempotent and not raise errors
    res2 = await seed_defaults(db_session)
    assert res2["seeded"] is True


@pytest.mark.asyncio
async def test_seed_refuses_in_production(db_session, monkeypatch):
    """seed_defaults must refuse to run in production."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = await seed_defaults(db_session)
    assert res["seeded"] is False
    assert res["reason"] == "production"


def test_worker_redis_client_has_no_socket_timeout(monkeypatch):
    """Verify that worker Redis connection does not have socket_timeout=0.5 (which crashes RQ)."""
    import fakeredis

    class FakeRedisNoTimeout(fakeredis.FakeRedis):
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("redis.from_url", lambda url, **kwargs: FakeRedisNoTimeout(**kwargs))
    # Reset singleton
    import app.worker.queue as wq
    wq._worker_redis_conn = None

    client = get_worker_redis_client()
    assert client is not None
    assert client.kwargs.get("socket_timeout") is None


@pytest.mark.asyncio
async def test_event_bus_redis_subscriber_feeding():
    """Verify feeding external Redis events delivers to active SSE subscriber queues."""
    test_tenant = "tenant-test-feed-123"
    test_doc = "doc-test-feed-456"

    # Start subscriber generator task
    subscriber_gen = event_bus.subscribe_tenant(test_tenant)
    sub_task = asyncio.create_task(subscriber_gen.__anext__())
    await asyncio.sleep(0.05)  # Yield to register queue in _tenant_subscribers

    # Feed an external event
    fed_event = {
        "event_id": "evt-ext-9999",
        "tenant_id": test_tenant,
        "document_id": test_doc,
        "stage": "ocr",
        "status": "processing",
        "progress_pct": 50,
        "details": {"test": "value"}
    }
    await event_bus.feed_external_event(fed_event)

    received_event = await sub_task
    assert received_event.get("event_id") == "evt-ext-9999"
    assert received_event.get("document_id") == test_doc
    assert received_event.get("stage") == "ocr"
    await subscriber_gen.aclose()


def test_port_8000_standardization():
    """Verify port 8000 is standardized across files and no 8080 or 8085 lingers."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Check frontend API default in api.ts
    api_ts_path = os.path.join(repo_root, "frontend", "src", "lib", "api.ts")
    with open(api_ts_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "8000" in content
    assert "8085" not in content
    assert "8080" not in content

    # Check docker-compose.yml
    dc_path = os.path.join(repo_root, "docker-compose.yml")
    with open(dc_path, "r", encoding="utf-8") as f:
        dc_content = f.read()
    assert '"8000:8000"' in dc_content
    assert "curl -f http://localhost:8000/health" in dc_content
    assert "8080" not in dc_content
    assert "8085" not in dc_content

    # Check scripts
    smoke_sh = os.path.join(repo_root, "scripts", "smoke_test.sh")
    with open(smoke_sh, "r", encoding="utf-8") as f:
        assert "8000" in f.read()
        assert "8080" not in f.read()

    smoke_py = os.path.join(repo_root, "scripts", "smoke_test.py")
    with open(smoke_py, "r", encoding="utf-8") as f:
        assert "8000" in f.read()
        assert "8085" not in f.read()


def test_requirements_split():
    """Verify runtime requirements is pinned without dev tools, and dev requirements includes pytest and fakeredis."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    req_path = os.path.join(repo_root, "backend", "requirements.txt")
    req_dev_path = os.path.join(repo_root, "backend", "requirements-dev.txt")

    with open(req_path, "r", encoding="utf-8") as f:
        req_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # All runtime requirements must be pinned with ==
    for line in req_lines:
        assert "==" in line, f"Requirement '{line}' in requirements.txt is not pinned"
        assert not line.startswith("pytest"), "pytest should not be in runtime requirements.txt"
        assert not line.startswith("fakeredis"), "fakeredis should not be in runtime requirements.txt"

    with open(req_dev_path, "r", encoding="utf-8") as f:
        dev_content = f.read()
    assert "pytest" in dev_content
    assert "pytest-asyncio" in dev_content
    assert "fakeredis" in dev_content
