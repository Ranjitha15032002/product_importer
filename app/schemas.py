# app/schemas.py
from pydantic import BaseModel, HttpUrl
from typing import Optional

# --- Product schemas ---
class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price_cents: Optional[int] = None
    active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = None
    active: Optional[bool] = None

class ProductOut(ProductBase):
    id: int

    class Config:
        orm_mode = True

# --- Webhook schemas ---
class WebhookBase(BaseModel):
    name: Optional[str] = None
    url: HttpUrl
    event: str
    enabled: Optional[bool] = True

class WebhookCreate(WebhookBase):
    pass

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    event: Optional[str] = None
    enabled: Optional[bool] = None

class WebhookOut(WebhookBase):
    id: int
    last_status: Optional[str] = None
    last_response_time_ms: Optional[int] = None

    class Config:
        orm_mode = True
