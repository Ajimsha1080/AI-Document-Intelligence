import hmac
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("webhook_service")

def generate_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    """Generates HMAC-SHA256 signature for webhook payload verification."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

async def dispatch_document_approved_webhook(
    tenant_id: str,
    document_id: str,
    document_data: Dict[str, Any],
    webhook_url: Optional[str] = None,
    secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs and signs a 'document.approved' webhook event payload.
    In compliance with security rules, webhook never dispatches without active transport,
    and returns dispatched=False with reason. No hardcoded secret is ever used.
    """
    now = datetime.now(timezone.utc).isoformat()
    signing_secret = secret or os.environ.get("WEBHOOK_SIGNING_SECRET") or settings.WEBHOOK_SIGNING_SECRET or ""

    event_payload = {
        "event": "document.approved",
        "tenant_id": tenant_id,
        "document_id": document_id,
        "timestamp": now,
        "data": document_data
    }

    signature = None
    if signing_secret:
        serialized = json.dumps(event_payload, sort_keys=True).encode("utf-8")
        signature = f"sha256={generate_webhook_signature(serialized, signing_secret)}"

    logger.info(
        f"Webhook evaluated for document {document_id} (Tenant: {tenant_id}) | "
        f"Webhook URL: {webhook_url or 'None'} | Dispatched: False"
    )

    reason = "no_webhook_endpoint_configured" if not webhook_url else "webhook_dispatch_offline"
    return {
        "dispatched": False,
        "reason": reason,
        "event": "document.approved",
        "document_id": document_id,
        "signature": signature,
        "timestamp": now,
        "target_url": webhook_url
    }
