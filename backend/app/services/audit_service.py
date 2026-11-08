from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.core.security import mask_pii_value

def sanitize_audit_payload(payload: Optional[Dict[str, Any]], mask_pii: bool = True) -> Optional[Dict[str, Any]]:
    if not payload:
        return None
    if not mask_pii:
        return payload
    
    sanitized = {}
    for k, v in payload.items():
        if isinstance(v, dict):
            sanitized[k] = sanitize_audit_payload(v, mask_pii=True)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_audit_payload(item, mask_pii=True) if isinstance(item, dict) else mask_pii_value(k, item)
                for item in v
            ]
        else:
            sanitized[k] = mask_pii_value(k, v)
    return sanitized

async def log_audit_event(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    mask_pii: bool = True,
) -> AuditLog:
    """
    Appends an immutable audit event to the database.
    Compliant with UAE Federal Decree-Law No. 45/2021 on Personal Data Protection.
    """
    clean_details = sanitize_audit_payload(details, mask_pii=mask_pii)
    
    audit_entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=clean_details
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry
