from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.services.model_engine.factory import get_model_provider
import logging
import sys

# Configure Sovereign Audit & Compliance Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] [UAE-REGION:%(region)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("uae_compliance")

class RegionLogFilter(logging.Filter):
    def filter(self, record):
        record.region = settings.CURRENT_REGION
        return True

for handler in logging.root.handlers:
    handler.addFilter(RegionLogFilter())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce strict startup checks
    logger.info("Initializing UAE Document Intelligence Sovereign Gateway...")
    logger.info(f"Compliance Region: {settings.CURRENT_REGION}")
    logger.info(f"Strict Local Only Boundary: {settings.STRICT_LOCAL_ONLY}")
    logger.info(f"CORS Allowed Origins: {settings.ALLOWED_ORIGINS}")
    
    # Audit local OCR readiness
    from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
    ocr_info = LocalOCRAdapter.get_ocr_info()
    loaded_langs = ocr_info.get("ocr_languages", [])
    logger.info(f"Local OCR Engine: {ocr_info.get('ocr_engine')} | Loaded Languages: {loaded_langs}")
    
    if "ara" not in loaded_langs:
        logger.warning(
            "HONESTY COMPLIANCE WARNING: Arabic OCR language pack ('ara') is missing from the host! "
            "Arabic document extraction will fail or report null fields until tesseract-ocr-ara is installed."
        )

    if settings.STRICT_LOCAL_ONLY:
        logger.info("UAE Sovereign Guard ACTIVE: Egress to non-whitelisted cross-border endpoints is blocked.")
        
    yield
    logger.info("Shutting down UAE Sovereign Gateway safely.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Tenant Document Intelligence SaaS compliant with UAE PDPL Federal Decree-Law No. 45/2021",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware with strict origin validation
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def uae_compliance_headers_middleware(request: Request, call_next):
    """Enforces sovereign data processing headers on all requests and responses."""
    try:
        provider = get_model_provider()
        actual_backend = getattr(provider, "backend_name", settings.MODEL_PROVIDER_BACKEND)
    except Exception:
        actual_backend = "unavailable"

    response = await call_next(request)
    response.headers["X-Data-Sovereignty-Region"] = settings.CURRENT_REGION
    response.headers["X-Compliance-PDPL"] = "UAE-Federal-Law-45-2021"
    response.headers["X-Model-Provider-Mode"] = actual_backend
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health & Compliance"])
async def health_check():
    """
    Sovereign health check listing:
    - OCR engine & loaded languages
    - Database connection status
    - Redis queue connection status
    - Storage connection status
    - Model backend
    Reports unvarnished truth; never silently falls back.
    """
    from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    import os

    ocr_info = LocalOCRAdapter.get_ocr_info()
    engine_name = ocr_info.get("ocr_engine", "none")
    loaded_langs = ocr_info.get("ocr_languages", [])
    ocr_available = LocalOCRAdapter.is_available()

    # 1. Database connection check
    db_status = "healthy"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # 2. Redis queue check
    redis_status = "healthy"
    try:
        from app.worker.queue import get_redis_client
        client = get_redis_client()
        if client is not None:
            client.ping()
        else:
            redis_status = "unavailable"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    # 3. Storage check
    storage_status = "healthy"
    try:
        if not os.path.exists(settings.LOCAL_STORAGE_DIR):
            os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"

    # 4. Model Provider Backend
    try:
        provider = get_model_provider()
        actual_backend = getattr(provider, "backend_name", settings.MODEL_PROVIDER_BACKEND)
        is_mock = getattr(provider, "is_mock", False)
    except Exception as e:
        actual_backend = f"unavailable: {str(e)}"
        is_mock = False

    overall_healthy = (
        db_status == "healthy" and
        ("unhealthy" not in redis_status) and
        storage_status == "healthy"
    )

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "region": settings.CURRENT_REGION,
        "strict_local_only": settings.STRICT_LOCAL_ONLY,
        "in_country_storage": settings.ENFORCE_IN_COUNTRY_STORAGE,
        "database": db_status,
        "redis": redis_status,
        "storage": storage_status,
        "model_backend": actual_backend,
        "model_backend_configured": settings.MODEL_PROVIDER_BACKEND,
        "is_mock": is_mock,
        "ocr_engine": engine_name,
        "ocr_languages": loaded_langs,
    }
