from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings

from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base_class import Base
# Import all models so Base knows about them before creation
from app.models.tenant import Tenant

from sqlalchemy.future import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Auto-create a default test tenant so the user doesn't have to deal with login
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.api_key == "default_test_key"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            import uuid
            new_tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Local Test Tenant",
                api_key="default_test_key"
            )
            session.add(new_tenant)
            await session.commit()
            
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade multi-tenant RAG platform API",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Add CORS middleware (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "message": "API is up and running"}

