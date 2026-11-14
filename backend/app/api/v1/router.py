from fastapi import APIRouter
from app.api.v1 import auth, tenants, users, document_types, audit, documents

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(users.router)
api_router.include_router(document_types.router)
api_router.include_router(documents.router)
api_router.include_router(audit.router)
