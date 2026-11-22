from contextlib import asynccontextmanager
import asyncio
import json
from fastapi import FastAPI, Request, Response
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

    # Run idempotent seed if enabled (never in production)
    from app.core.seed import run_seed_if_enabled
    try:
        await run_seed_if_enabled()
    except Exception as e:
        logger.error(f"Startup seeding error: {e}")

    # Start redis.asyncio subscriber on "tenant:*:events" feeding event_bus SSE queues
    redis_listener_task = None
    try:
        import redis.asyncio as aioredis
        from app.services.event_bus import event_bus

        async def listen_redis_events():
            r = None
            try:
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                pubsub = r.pubsub()
                await pubsub.psubscribe("tenant:*:events")
                logger.info("Connected redis.asyncio subscriber to 'tenant:*:events'")
                async for message in pubsub.listen():
                    if message and message.get("type") in ("pmessage", "message"):
                        raw_data = message.get("data")
                        if isinstance(raw_data, str):
                            try:
                                event_payload = json.loads(raw_data)
                                await event_bus.feed_external_event(event_payload)
                            except Exception as pe:
                                logger.debug(f"Failed to parse redis event json: {pe}")
            except asyncio.CancelledError:
                pass
            except Exception as re:
                logger.warning(f"Redis event subscriber encountered error: {re}")
            finally:
                if r:
                    try:
                        await r.aclose()
                    except Exception:
                        pass

        redis_listener_task = asyncio.create_task(listen_redis_events())
    except Exception as exc:
        logger.warning(f"Could not initialize Redis event subscriber: {exc}")

    yield

    if redis_listener_task and not redis_listener_task.done():
        redis_listener_task.cancel()
        try:
            await redis_listener_task
        except (asyncio.CancelledError, Exception):
            pass

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
async def health_check(response: Response):
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

    if actual_backend == "local" and not ocr_available:
        actual_backend = "mock-fallback"
        is_mock = True

    response.headers["x-model-provider-mode"] = actual_backend

    # 5. Check actually loaded models
    from app.services.rag.providers import (
        FastEmbedMultilingualProvider,
        check_ollama_reachable,
        get_loaded_models
    )
    models_loaded = get_loaded_models()

    if FastEmbedMultilingualProvider._singleton_model is not None:
        rag_embedding_engine = f"fastembed/{FastEmbedMultilingualProvider._singleton_model_name}"
    else:
        rag_embedding_engine = "local_hashing/128dim"

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    ollama_model = os.environ.get("DOCS_LLM_MODEL", "qwen2.5:3b")
    ollama_online = await check_ollama_reachable(ollama_host, timeout=0.5)
    if ollama_online:
        rag_generator = f"local_ollama/{ollama_model}"
        models_loaded.append(rag_generator)
    else:
        rag_generator = "sovereign_local_generator"

    if ocr_available and engine_name != "none":
        models_loaded.append(f"ocr/{engine_name}")

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
        "rag_embedding_engine": rag_embedding_engine,
        "rag_generator": rag_generator,
        "models_loaded": models_loaded,
    }
