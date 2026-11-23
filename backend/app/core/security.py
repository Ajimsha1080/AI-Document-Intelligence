from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
import bcrypt
import jwt
import secrets
import hashlib
import re

from app.core.config import settings

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(
    subject: Union[str, Any],
    tenant_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    scope: Optional[str] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "role": role,
        "iss": "uae-doc-intel-auth",
        "aud": "uae-doc-intel-services",
    }
    if scope:
        to_encode["scope"] = scope
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        audience="uae-doc-intel-services",
        issuer="uae-doc-intel-auth",
    )

def generate_api_key(tenant_id: str) -> tuple[str, str, str]:
    """Generates (raw_key, key_hash, prefix)"""
    token = secrets.token_urlsafe(32)
    prefix = token[:8]
    raw_key = f"uae_live_{prefix}_{token}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash, prefix

def mask_pii_value(key: str, val: Any) -> Any:
    """Masks PII values for privacy previews, exports, and sanitized audit trails."""
    if not isinstance(val, str) or not val:
        return val
    
    clean_key = key.lower()
    
    # Emirates ID pattern (784-XXXX-XXXXXXX-X)
    if any(k in clean_key for k in ["emirates_id", "eid", "id_number", "national_id"]) or re.match(r"^784-\d{4}-\d{7}-\d{1}$", val) or val.startswith("784-"):
        parts = val.split("-")
        if len(parts) == 4:
            return f"{parts[0]}-****-*******-{parts[3]}"
        return f"{parts[0]}-****-*******-{val[-1]}" if len(parts) >= 2 else (f"{val[:4]}****{val[-2:]}" if len(val) > 6 else "****")

    # TRN pattern (15 digits starting with 100)
    if any(k in clean_key for k in ["trn", "tax_registration_number"]) or re.match(r"^100\d{12}$", val):
        return f"{val[:3]}*********{(val[-3:] if len(val) >= 3 else '')}"
        
    # Email pattern
    if "email" in clean_key or "@" in val:
        parts = val.split("@")
        if len(parts) == 2:
            name, domain = parts
            masked_name = name[0] + "***" + (name[-1] if len(name) > 1 else "")
            return f"{masked_name}@{domain}"
            
    # Phone numbers
    if "phone" in clean_key or "mobile" in clean_key:
        return f"{val[:4]}****{val[-2:]}" if len(val) > 6 else "****"
        
    # Passport / License / IBAN
    if any(k in clean_key for k in ["passport", "iban", "account"]):
        return f"{val[:2]}****{val[-3:]}" if len(val) > 5 else "****"
        
    return val

def mask_pii_text(text: str) -> str:
    """Masks Emirates IDs, emails, and phone numbers in free-form text or RAG output."""
    if not isinstance(text, str) or not text:
        return text

    # Emirates ID: 784-XXXX-XXXXXXX-X
    def _mask_eid(m):
        full = m.group(0)
        parts = full.split("-")
        return f"{parts[0]}-****-*******-{parts[3]}"

    text = re.sub(r"\b784-\d{4}-\d{7}-\d\b", _mask_eid, text)

    # TRN: 15 digits starting with 100
    def _mask_trn(m):
        full = m.group(0)
        return f"{full[:3]}*********{(full[-3:] if len(full) >= 3 else '')}"

    text = re.sub(r"\b100\d{12}\b", _mask_trn, text)

    # Emails
    def _mask_email(m):
        full = m.group(0)
        parts = full.split("@")
        if len(parts) == 2:
            name, dom = parts
            return f"{name[0]}***@{dom}"
        return "****"

    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", _mask_email, text)

    # UAE Phone Numbers
    text = re.sub(r"(\+971|00971|0)(?:50|51|52|54|55|56|58|2|3|4|6|7|9)\d{7}", r"\1-XX-***XXXX", text)
    return text
