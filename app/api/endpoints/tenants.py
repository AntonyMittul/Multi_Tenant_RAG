from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy
from typing import List

from app.api import deps
from app.crud import crud_tenant
from app.schemas.tenant import TenantCreate, TenantResponse, TenantWithAPIKey
from app.models.tenant import Tenant

router = APIRouter()

# Note: In a real production system, tenant creation should be protected by
# an Admin/Superuser authentication mechanism, not exposed publicly.
# For learning purposes, we are keeping it simple here.

@router.post("/", response_model=TenantWithAPIKey, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Create a new tenant. 
    Returns the newly created tenant along with their auto-generated API Key.
    IMPORTANT: This is the only time the raw API key is returned.
    """
    try:
        tenant = await crud_tenant.create_tenant(db, tenant=tenant_in)
        return tenant
    except sqlalchemy.exc.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists. Please choose a different name."
        )

@router.get("/", response_model=List[TenantResponse])
async def read_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Retrieve all tenants (admin only in real scenarios).
    """
    tenants = await crud_tenant.get_tenants(db, skip=skip, limit=limit)
    return tenants

@router.get("/me", response_model=TenantResponse)
async def read_tenant_me(
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Get information about the currently authenticated tenant.
    """
    return current_tenant

