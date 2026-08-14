from pydantic import BaseModel, ConfigDict
from typing import Optional

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    pass

class TenantUpdate(TenantBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class TenantInDBBase(TenantBase):
    id: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class TenantResponse(TenantInDBBase):
    pass

class TenantWithAPIKey(TenantInDBBase):
    api_key: str

