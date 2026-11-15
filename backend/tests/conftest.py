import sys
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import Base, get_db
import app.models  # Ensure all ORM models are registered
from app.main import app as fastapi_app
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password, create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

fastapi_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def seeded_data(db_session: AsyncSession):
    # Tenant 1: Abu Dhabi Commercial Bank
    tenant_1 = Tenant(
        id="11111111-1111-1111-1111-111111111111",
        name="ADCB Banking Group",
        slug="adcb-demo",
        tier="enterprise",
        retention_days=180,
        pii_masking_default=True
    )
    # Tenant 2: Emirates NBD
    tenant_2 = Tenant(
        id="22222222-2222-2222-2222-222222222222",
        name="Emirates NBD",
        slug="enbd-demo",
        tier="enterprise",
        retention_days=365,
        pii_masking_default=True
    )
    db_session.add_all([tenant_1, tenant_2])
    await db_session.flush()

    # Tenant 1 Admin
    admin_user = User(
        id="aaaa1111-1111-1111-1111-111111111111",
        tenant_id=tenant_1.id,
        email="admin@adcb.ae",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Ahmed Al Mansoori",
        role="admin"
    )
    # Tenant 1 Reviewer
    reviewer_user = User(
        id="bbbb1111-1111-1111-1111-111111111111",
        tenant_id=tenant_1.id,
        email="reviewer@adcb.ae",
        hashed_password=hash_password("ReviewerPass123!"),
        full_name="Fatima Al Zaabi",
        role="reviewer"
    )
    # Tenant 1 Viewer
    viewer_user = User(
        id="cccc1111-1111-1111-1111-111111111111",
        tenant_id=tenant_1.id,
        email="viewer@adcb.ae",
        hashed_password=hash_password("ViewerPass123!"),
        full_name="Rashid Al Nuaimi",
        role="viewer"
    )

    # Tenant 2 Admin
    tenant2_admin = User(
        id="aaaa2222-2222-2222-2222-222222222222",
        tenant_id=tenant_2.id,
        email="admin@enbd.ae",
        hashed_password=hash_password("AdminEnbd123!"),
        full_name="Khalid Al Falasi",
        role="admin"
    )

    db_session.add_all([admin_user, reviewer_user, viewer_user, tenant2_admin])
    await db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "admin_user": admin_user,
        "reviewer_user": reviewer_user,
        "viewer_user": viewer_user,
        "tenant2_admin": tenant2_admin,
        "admin_token": create_access_token(admin_user.id, tenant_1.id, "admin"),
        "reviewer_token": create_access_token(reviewer_user.id, tenant_1.id, "reviewer"),
        "viewer_token": create_access_token(viewer_user.id, tenant_1.id, "viewer"),
        "tenant2_token": create_access_token(tenant2_admin.id, tenant_2.id, "admin"),
    }
