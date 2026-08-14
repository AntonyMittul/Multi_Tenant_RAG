from fastapi import APIRouter
from app.api.endpoints import tenants, documents, search, generate, evaluate

api_router = APIRouter()
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(evaluate.router, prefix="/evaluate", tags=["evaluate"])
