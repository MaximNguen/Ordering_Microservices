import uuid

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    """Shared fields for product requests and responses."""

    model_config = ConfigDict(from_attributes=True)
    name: str
    description: str | None = None
    price: float


class ProductCreate(ProductBase):
    """Schema for product creation."""


class ProductUpdate(BaseModel):
    """Schema for product updates."""

    model_config = ConfigDict(from_attributes=True)
    name: str | None = None
    description: str | None = None
    price: float | None = None


class ProductResponse(ProductBase):
    """Schema for product responses."""

    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
