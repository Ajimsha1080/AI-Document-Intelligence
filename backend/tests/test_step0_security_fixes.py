import pytest
from httpx import AsyncClient
from app.core.config import Settings, DEFAULT_SECRET_KEY, DEFAULT_ADMIN_PASSWORD
from app.core.rate_limit import login_rate_limiter
from app.services.model_engine.factory import get_model_provider

@pytest.mark.asyncio
async def test_production_refusal_on_default_secrets():
    """
    Step 0: Refuse to start when ENVIRONMENT=production and SECRET_KEY,
    admin password, S3 keys, or DB password are still the defaults.
    """
    # 1. Default SECRET_KEY in production
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=DEFAULT_SECRET_KEY,
            DEFAULT_ADMIN_PASSWORD="CustomAdminPassword123!",
            S3_ACCESS_KEY="custom_s3_key",
            S3_SECRET_KEY="custom_s3_secret_32_chars_minimum",
            DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@uae-pg:5432/docintel"
        )
    assert "FATAL SECURITY VIOLATION" in str(exc_info.value)
    assert "SECRET_KEY" in str(exc_info.value)

    # 2. Default admin password in production
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            DEFAULT_ADMIN_PASSWORD=DEFAULT_ADMIN_PASSWORD,
            S3_ACCESS_KEY="custom_s3_key",
            S3_SECRET_KEY="custom_s3_secret_32_chars_minimum",
            DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@uae-pg:5432/docintel"
        )
    assert "DEFAULT_ADMIN_PASSWORD" in str(exc_info.value)

    # 3. Default S3 keys in production
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            DEFAULT_ADMIN_PASSWORD="CustomAdminPassword123!",
            S3_ACCESS_KEY="minioadmin",
            S3_SECRET_KEY="minioadmin",
            DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@uae-pg:5432/docintel"
        )
    assert "S3_ACCESS_KEY" in str(exc_info.value)

    # 4. SQLite or default postgres credentials in production
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            DEFAULT_ADMIN_PASSWORD="CustomAdminPassword123!",
            S3_ACCESS_KEY="custom_s3_key",
            S3_SECRET_KEY="custom_s3_secret_32_chars_minimum",
            DATABASE_URL="sqlite+aiosqlite:///./docsmvp.db"
        )
    assert "DATABASE_URL" in str(exc_info.value)

    # 5. Mock model backend in production must be refused
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            DEFAULT_ADMIN_PASSWORD="CustomAdminPassword123!",
            S3_ACCESS_KEY="custom_s3_key",
            S3_SECRET_KEY="custom_s3_secret_32_chars_minimum",
            DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@uae-pg:5432/docintel",
            MODEL_PROVIDER_BACKEND="mock"
        )
    assert "MODEL_PROVIDER_BACKEND" in str(exc_info.value)

    # 6. Clean production settings should pass validation
    prod_valid = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 32,
        DEFAULT_ADMIN_PASSWORD="StrongProdPassword2026!#",
        S3_ACCESS_KEY="sovereign_minio_user",
        S3_SECRET_KEY="sovereign_minio_secure_key_1234",
        DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@uae-pg:5432/docintel"
    )
    assert prod_valid.ENVIRONMENT == "production"

@pytest.mark.asyncio
async def test_cors_no_wildcard_with_credentials():
    """
    Step 0: Restrict CORS to an ALLOWED_ORIGINS env list. No '*' with credentials.
    """
    # Wildcard '*' is stripped automatically to prevent insecure wildcard credentials
    s = Settings(ALLOWED_ORIGINS="https://bank.uae.ae, *")
    assert "*" not in s.ALLOWED_ORIGINS
    assert "https://bank.uae.ae" in s.ALLOWED_ORIGINS

@pytest.mark.asyncio
async def test_health_reports_real_model_backend(async_client: AsyncClient, monkeypatch):
    """
    Step 0: Make /health report the REAL model backend deterministically.
    If 'local' has no real engine loaded, report 'mock-fallback' and log a warning.
    When real engine is loaded, report 'local'.
    Never silently fall back.
    """
    from app.services.model_engine.local_ocr_adapter import LocalOCRAdapter

    # Case 1: Real OCR engine is not available -> returns mock-fallback
    monkeypatch.setattr(LocalOCRAdapter, "is_available", classmethod(lambda cls: False))
    monkeypatch.setattr(LocalOCRAdapter, "get_ocr_info", classmethod(lambda cls: {"ocr_engine": "none", "ocr_languages": []}))
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_backend"] == "mock-fallback"
    assert data["model_backend_configured"] == "local"
    assert data["is_mock"] is True
    assert data["ocr_engine"] == "none"
    assert data["ocr_languages"] == []
    assert "database" in data
    assert "redis" in data
    assert "storage" in data
    assert resp.headers.get("x-model-provider-mode") == "mock-fallback"

    # Case 2: Real OCR engine is available -> returns local and loaded languages
    monkeypatch.setattr(LocalOCRAdapter, "is_available", classmethod(lambda cls: True))
    monkeypatch.setattr(LocalOCRAdapter, "get_ocr_info", classmethod(lambda cls: {"ocr_engine": "tesseract", "ocr_languages": ["ara", "eng", "osd"]}))
    resp_real = await async_client.get("/health")
    assert resp_real.status_code == 200
    data_real = resp_real.json()
    assert data_real["model_backend"] == "local"
    assert data_real["is_mock"] is False
    assert data_real["ocr_engine"] == "tesseract"
    assert "ara" in data_real["ocr_languages"]
    assert "eng" in data_real["ocr_languages"]
    assert resp_real.headers.get("x-model-provider-mode") == "local"

@pytest.mark.asyncio
async def test_login_rate_limiting_and_temporary_lockout(async_client: AsyncClient, seeded_data: dict):
    """
    Step 0: Add login rate limiting and temporary lockout after repeated failures (5 failures).
    """
    login_rate_limiter.reset()
    target_email = seeded_data["reviewer_user"].email

    # Attempts 1 to 4 should return 401 UNAUTHORIZED
    for attempt in range(1, 5):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": target_email, "password": f"WrongPassword_{attempt}"}
        )
        assert resp.status_code == 401, f"Attempt {attempt} should be 401"
        assert "Incorrect email or password" in resp.json()["detail"]

    # 5th failed attempt must engage lockout and return 429 TOO MANY REQUESTS
    resp_5 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": target_email, "password": "WrongPassword_5"}
    )
    assert resp_5.status_code == 429
    assert "Maximum failed login attempts exceeded" in resp_5.json()["detail"]
    assert "Retry-After" in resp_5.headers

    # 6th attempt while locked out must immediately be blocked with 429, even with correct password
    resp_locked = await async_client.post(
        "/api/v1/auth/login",
        json={"email": target_email, "password": "CorrectReviewerPass2026!"}
    )
    assert resp_locked.status_code == 429

    # Clean up rate limiter after test
    login_rate_limiter.reset()
