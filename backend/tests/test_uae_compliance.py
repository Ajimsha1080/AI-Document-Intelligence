import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from app.core.config import Settings

@pytest.mark.asyncio
async def test_health_check_sovereignty_headers(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["strict_local_only"] is True
    assert data["in_country_storage"] is True

    # Validate compliance headers
    assert resp.headers.get("x-data-sovereignty-region") == "uae-north"
    assert resp.headers.get("x-compliance-pdpl") == "UAE-Federal-Law-45-2021"

@pytest.mark.asyncio
async def test_cross_border_endpoint_violation():
    # Attempting to configure foreign cloud API endpoints without sovereign approval should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(
            IN_REGION_API_ENDPOINT="https://api.openai.com/v1",
            STRICT_LOCAL_ONLY=True
        )

    with pytest.raises(ValidationError):
        Settings(
            IN_REGION_API_ENDPOINT="https://api.anthropic.com/v1",
            STRICT_LOCAL_ONLY=True
        )
