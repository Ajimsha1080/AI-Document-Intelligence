import os
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document_type import DocumentType
from app.schemas.document_type import (
    DEFAULT_EMIRATES_ID_SCHEMA,
    DEFAULT_TRADE_LICENSE_SCHEMA,
    DEFAULT_COMMERCIAL_INVOICE_SCHEMA,
)

logger = logging.getLogger("uae_compliance")

async def seed_defaults(db: AsyncSession) -> dict:
    """
    Idempotently seeds default tenant, admin, and the 3 document types.
    Strictly refuses to run in production.
    """
    if settings.ENVIRONMENT.lower() == "production":
        logger.warning("SEED_DEFAULTS skipped: refusing to seed default accounts in production environment.")
        return {"seeded": False, "reason": "production"}

    # 1. Tenant
    tenant_id = settings.DEFAULT_TENANT_ID
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            id=tenant_id,
            name=settings.DEFAULT_TENANT_NAME,
            slug="default-tenant",
            tier="enterprise",
            retention_days=365,
            pii_masking_default=True,
            is_active=True
        )
        db.add(tenant)
        await db.flush()
        logger.info(f"Seeded default tenant: {tenant.name} ({tenant.id})")

    # 2. Admin User
    admin_email = settings.DEFAULT_ADMIN_EMAIL.strip().lower()
    user_res = await db.execute(select(User).where(User.email == admin_email))
    admin_user = user_res.scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            tenant_id=tenant.id,
            email=admin_email,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            full_name="Default Platform Admin",
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        await db.flush()
        logger.info(f"Seeded default admin user: {admin_user.email}")

    # 3. 3 Document Types: Emirates ID, Trade License, Commercial Invoice
    doc_types_specs = [
        {
            "code": "emirates_id",
            "name_en": "UAE Identity Card (Emirates ID)",
            "name_ar": "بطاقة الهوية الإماراتية",
            "description": "Federal Authority for Identity and Citizenship (ICP) National ID card",
            "schema_definition": DEFAULT_EMIRATES_ID_SCHEMA.model_dump(),
        },
        {
            "code": "uae_trade_license",
            "name_en": "UAE Commercial Trade License",
            "name_ar": "رخصة تجارية في دولة الإمارات",
            "description": "Department of Economy and Tourism (DET / DED / Freezones) commercial license",
            "schema_definition": DEFAULT_TRADE_LICENSE_SCHEMA.model_dump(),
        },
        {
            "code": "commercial_invoice",
            "name_en": "UAE Commercial Tax Invoice",
            "name_ar": "فاتورة ضريبية تجارية",
            "description": "Federal Tax Authority (FTA) compliant commercial invoice with TRN",
            "schema_definition": DEFAULT_COMMERCIAL_INVOICE_SCHEMA.model_dump(),
        },
    ]

    for spec in doc_types_specs:
        dt_res = await db.execute(
            select(DocumentType).where(
                DocumentType.tenant_id == tenant.id,
                DocumentType.code == spec["code"]
            )
        )
        dt = dt_res.scalar_one_or_none()
        if not dt:
            dt = DocumentType(
                tenant_id=tenant.id,
                code=spec["code"],
                name_en=spec["name_en"],
                name_ar=spec["name_ar"],
                description=spec["description"],
                schema_definition=spec["schema_definition"],
                is_active=True
            )
            db.add(dt)
            logger.info(f"Seeded document type: {spec['code']}")

    await db.commit()
    return {"seeded": True, "tenant_id": tenant.id, "admin_email": admin_email}


async def run_seed_if_enabled():
    """Triggered on startup when SEED_DEFAULTS=true, never in production."""
    if settings.ENVIRONMENT.lower() == "production":
        return
    if getattr(settings, "SEED_DEFAULTS", False) or os.environ.get("SEED_DEFAULTS", "").lower() == "true":
        async with AsyncSessionLocal() as session:
            await seed_defaults(session)
