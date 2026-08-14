from fastapi import Depends, HTTPException, status, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.crud import crud_tenant
from app.models.tenant import Tenant

# We expect an API key in the X-API-Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    api_key: str = Security(api_key_header)
) -> Tenant:
    """
    Dependency to get the current tenant based on the provided API key.
    """
    tenant = await crud_tenant.get_tenant_by_api_key(db, api_key=api_key)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials - Invalid API Key",
        )
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive tenant",
        )
    return tenant

