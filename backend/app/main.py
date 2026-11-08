import sys
import os
# Ensure backend directory is in sys.path regardless of launch working directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document_type import DocumentType
from app.schemas.document_type import DEFAULT_EMIRATES_ID_SCHEMA, DEFAULT_TRADE_LICENSE_SCHEMA
from app.services.audit_service import log_audit_event
from app.api.v1.router import api_router
import app.models  # Register all ORM models

async def seed_initial_data():
    """Seeds default tenant, admin user, and standard UAE schemas if database is newly initialized."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Tenant).where(Tenant.id == settings.DEFAULT_TENANT_ID))
        tenant = res.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                id=settings.DEFAULT_TENANT_ID,
                name=settings.DEFAULT_TENANT_NAME,
                slug="alhilal-demo",
                tier="enterprise",
                retention_days=365,
                pii_masking_default=True,
                is_active=True
            )
            db.add(tenant)
            await db.flush()

            admin_user = User(
                tenant_id=tenant.id,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="UAE Compliance Director",
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            await db.flush()

            # Seed standard schemas
            eid_type = DocumentType(
                tenant_id=tenant.id,
                code="emirates_id",
                name_en="UAE Identity Card (Emirates ID)",
                name_ar="بطاقة الهوية الإماراتية",
                description="Federal Authority for Identity and Citizenship (ICP) National ID card",
                schema_definition=DEFAULT_EMIRATES_ID_SCHEMA.model_dump(),
                is_active=True
            )
            trade_type = DocumentType(
                tenant_id=tenant.id,
                code="uae_trade_license",
                name_en="UAE Commercial Trade License",
                name_ar="رخصة تجارية في دولة الإمارات",
                description="Department of Economy and Tourism (DET) commercial license",
                schema_definition=DEFAULT_TRADE_LICENSE_SCHEMA.model_dump(),
                is_active=True
            )
            db.add_all([eid_type, trade_type])
            await db.flush()

            # Log audit trail
            await log_audit_event(
                db=db,
                tenant_id=tenant.id,
                actor_id=admin_user.id,
                actor_email=admin_user.email,
                actor_role="admin",
                action="SYSTEM_INITIALIZED",
                entity_type="tenant",
                entity_id=tenant.id,
                details={"initial_seed": True, "schemas": ["emirates_id", "uae_trade_license"]}
            )
            await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed bootstrap data if empty
    await seed_initial_data()
    yield
    # Cleanup on shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-tenant Document Intelligence Platform tailored for the UAE market (Banking, KYC, Trade)",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to tenant sovereign domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def uae_compliance_headers_middleware(request: Request, call_next):
    """Enforces sovereign data processing headers on all requests and responses."""
    response = await call_next(request)
    response.headers["X-Data-Sovereignty-Region"] = settings.CURRENT_REGION
    response.headers["X-Compliance-PDPL"] = "UAE-Federal-Law-45-2021"
    response.headers["X-Model-Provider-Mode"] = settings.MODEL_PROVIDER_BACKEND
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health & Compliance"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "region": settings.CURRENT_REGION,
        "strict_local_only": settings.STRICT_LOCAL_ONLY,
        "in_country_storage": settings.ENFORCE_IN_COUNTRY_STORAGE,
        "model_backend": settings.MODEL_PROVIDER_BACKEND,
    }
