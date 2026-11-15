from fastapi import APIRouter
from app.api.v1 import auth, tenants, users, document_types, audit, documents, rag
from app.api.v1.documents import stream_tenant_events

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(users.router)
api_router.include_router(document_types.router)
api_router.include_router(documents.router)
api_router.include_router(audit.router)
api_router.include_router(rag.router)

# Tenant-scoped event stream at /api/v1/events
api_router.add_api_route("/events", stream_tenant_events, methods=["GET"], tags=["Events"])

