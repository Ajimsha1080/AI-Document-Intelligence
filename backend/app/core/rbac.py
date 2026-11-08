from enum import Enum
from typing import Set, Dict

class UserRole(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    API_CLIENT = "api_client"

class Permission(str, Enum):
    # Tenant & System
    TENANT_MANAGE = "tenant:manage"
    USER_MANAGE = "user:manage"
    SCHEMA_MANAGE = "schema:manage"
    AUDIT_VIEW = "audit:view"
    RETENTION_MANAGE = "retention:manage"
    
    # Document Lifecycle
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_REVIEW = "document:review"       # Edit/correct extracted fields
    DOCUMENT_APPROVE = "document:approve"     # Mark as approved
    DOCUMENT_EXPORT = "document:export"       # Export structured CSV/JSON
    DOCUMENT_DELETE = "document:delete"       # Delete document & derived data

ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.TENANT_MANAGE,
        Permission.USER_MANAGE,
        Permission.SCHEMA_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.RETENTION_MANAGE,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_REVIEW,
        Permission.DOCUMENT_APPROVE,
        Permission.DOCUMENT_EXPORT,
        Permission.DOCUMENT_DELETE,
    },
    UserRole.REVIEWER: {
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_REVIEW,
        Permission.DOCUMENT_APPROVE,
        Permission.DOCUMENT_EXPORT,
    },
    UserRole.VIEWER: {
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_EXPORT,
    },
    UserRole.API_CLIENT: {
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_EXPORT,
    },
}

def has_permission(role: str, permission: Permission) -> bool:
    try:
        user_role = UserRole(role)
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    except ValueError:
        return False
