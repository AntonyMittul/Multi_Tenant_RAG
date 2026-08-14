from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
import secrets

async def get_tenant(db: AsyncSession, tenant_id: str) -> Tenant | None:
    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    return result.scalars().first()

async def get_tenant_by_api_key(db: AsyncSession, api_key: str) -> Tenant | None:
    result = await db.execute(select(Tenant).filter(Tenant.api_key == api_key))
    return result.scalars().first()

async def create_tenant(db: AsyncSession, tenant: TenantCreate) -> Tenant:
    # Generate a secure API key
    api_key = secrets.token_urlsafe(32)
    db_tenant = Tenant(name=tenant.name, api_key=api_key)
    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)
    return db_tenant

async def get_tenants(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Tenant]:
    result = await db.execute(select(Tenant).offset(skip).limit(limit))
    return result.scalars().all()

