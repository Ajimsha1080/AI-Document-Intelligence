from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import sys
import logging

logger = logging.getLogger("uae_compliance")

class Settings(BaseSettings):
    PROJECT_NAME: str = "UAE Document Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_generate_with_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # UAE Compliance & Data Sovereignty
    STRICT_LOCAL_ONLY: bool = True
    ENFORCE_IN_COUNTRY_STORAGE: bool = True
    ALLOWED_DATA_REGIONS: List[str] = ["uae-north", "uae-central", "local-cluster"]
    CURRENT_REGION: str = "uae-north"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./docsmvp.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Object Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "uae-documents"
    S3_REGION: str = "uae-central"
    
    # Model Provider ("local" | "uae_in_region" | "mock")
    MODEL_PROVIDER_BACKEND: str = "local"
    IN_REGION_API_ENDPOINT: Optional[str] = None

    # Default Seed Tenant & Admin for Local & Staging Environment
    DEFAULT_TENANT_ID: str = "00000000-0000-0000-0000-000000000001"
    DEFAULT_TENANT_NAME: str = "Al Hilal Banking & Capital"
    DEFAULT_ADMIN_EMAIL: str = "admin@alhilal-demo.ae"
    DEFAULT_ADMIN_PASSWORD: str = "AdminSecurePass2026!"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @field_validator("IN_REGION_API_ENDPOINT")
    @classmethod
    def validate_in_region_endpoint(cls, v: Optional[str], info) -> Optional[str]:
        if not v:
            return v
        # Ensure we do not inadvertently call standard non-UAE US/EU endpoints
        forbidden_hosts = ["api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com"]
        for forbidden in forbidden_hosts:
            if forbidden in v.lower():
                raise ValueError(
                    f"UAE Compliance Violation: Outbound endpoint {v} is located outside UAE sovereign jurisdiction. "
                    f"Cross-border transfer of document intelligence data is prohibited."
                )
        return v

settings = Settings()
