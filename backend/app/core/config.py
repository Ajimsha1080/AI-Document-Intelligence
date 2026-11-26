from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
import os
import sys
import logging

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_canonical_db_path = os.path.join(_project_root, "docsmvp.db").replace("\\", "/")

logger = logging.getLogger("uae_compliance")

DEFAULT_SECRET_KEY = "CHANGE_THIS_IN_PRODUCTION_generate_with_openssl_rand_hex_32"
DEFAULT_ADMIN_PASSWORD = "AdminSecurePass2026!"
DEFAULT_S3_ACCESS_KEY = "minioadmin"
DEFAULT_S3_SECRET_KEY = "minioadmin"

class Settings(BaseSettings):
    PROJECT_NAME: str = "UAE Document Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SEED_DEFAULTS: bool = False
    
    # Security
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days session validity
    PLATFORM_ADMIN_API_KEY: Optional[str] = None
    WEBHOOK_SIGNING_SECRET: Optional[str] = None
    
    # CORS Configuration - Explicit origin list, strictly no wildcard '*' with credentials
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3005",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3005",
    ]
    
    # Login Rate Limiting & Account Lockout
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # UAE Compliance & Data Sovereignty
    STRICT_LOCAL_ONLY: bool = True
    ENFORCE_IN_COUNTRY_STORAGE: bool = True
    ALLOWED_DATA_REGIONS: List[str] = ["uae-north", "uae-central", "local-cluster"]
    CURRENT_REGION: str = "uae-north"
    
    # Storage & Upload Limits
    MAX_UPLOAD_SIZE_MB: int = 25
    LOCAL_STORAGE_DIR: str = "./data/sovereign_storage"
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_canonical_db_path}"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Object Storage - Set via env or None for local sovereign storage
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL", None)
    S3_ACCESS_KEY: str = DEFAULT_S3_ACCESS_KEY
    S3_SECRET_KEY: str = DEFAULT_S3_SECRET_KEY
    S3_BUCKET_NAME: str = "uae-documents"
    S3_REGION: str = "uae-central"
    
    # Model Provider ("local" | "uae_in_region" | "mock")
    MODEL_PROVIDER_BACKEND: str = "local"
    IN_REGION_API_ENDPOINT: Optional[str] = None

    # Default Seed Tenant & Admin for Local & Staging Environment
    DEFAULT_TENANT_ID: str = "00000000-0000-0000-0000-000000000001"
    DEFAULT_TENANT_NAME: str = "Demo Bank (Sample)"
    DEFAULT_ADMIN_EMAIL: str = "admin@alhilal-demo.ae"
    DEFAULT_ADMIN_PASSWORD: str = DEFAULT_ADMIN_PASSWORD
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        else:
            origins = v
        # Ensure no wildcard '*' is permitted when credentials are used
        sanitized = [o for o in origins if o != "*"]
        if "*" in origins:
            logger.warning("CORS security: Wildcard '*' removed from ALLOWED_ORIGINS because credentials are enabled.")
        return sanitized if sanitized else ["http://localhost:3000", "http://localhost:3005"]

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

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """
        Enforces strict refusal to start in production environment if any secrets,
        admin passwords, S3 credentials, or DB passwords remain set to defaults.
        """
        if self.ENVIRONMENT.lower() == "production":
            violations = []
            if (
                self.SECRET_KEY == DEFAULT_SECRET_KEY
                or "CHANGE_THIS" in self.SECRET_KEY
                or "demo_dev_secret_key" in self.SECRET_KEY
                or "demo" in self.SECRET_KEY.lower()
                or "dev_secret" in self.SECRET_KEY.lower()
                or len(self.SECRET_KEY) < 32
            ):
                violations.append("SECRET_KEY is using a demo, development, or insecure key (min 32 chars required)")
            if not self.PLATFORM_ADMIN_API_KEY or len(self.PLATFORM_ADMIN_API_KEY.strip()) < 16:
                violations.append("PLATFORM_ADMIN_API_KEY must be configured in production (min 16 chars)")
            if self.DEFAULT_ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD:
                violations.append("DEFAULT_ADMIN_PASSWORD is still set to the default bootstrap password")
            if self.S3_ACCESS_KEY == DEFAULT_S3_ACCESS_KEY or self.S3_SECRET_KEY == DEFAULT_S3_SECRET_KEY:
                violations.append("S3_ACCESS_KEY / S3_SECRET_KEY are using default 'minioadmin' credentials")
            if "sqlite" in self.DATABASE_URL.lower():
                violations.append("DATABASE_URL is using SQLite instead of production PostgreSQL with pgvector")
            elif "postgres:postgres" in self.DATABASE_URL.lower():
                violations.append("DATABASE_URL is using default 'postgres:postgres' credentials")
            if self.MODEL_PROVIDER_BACKEND.lower() == "mock":
                violations.append("MODEL_PROVIDER_BACKEND is set to 'mock' which is forbidden in production")
                
            if violations:
                msg = (
                    "FATAL SECURITY VIOLATION: Refusing to start in PRODUCTION environment with default credentials:\n"
                    + "\n".join(f" - {v}" for v in violations)
                    + "\nYou must supply production sovereign secrets via environment variables."
                )
                logger.critical(msg)
                raise RuntimeError(msg)
        return self

settings = Settings()
