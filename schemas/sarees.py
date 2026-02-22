"""
Saree Schemas
Request and response models for saree endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


class SareeBase(BaseModel):
    """Base saree schema"""
    name: str = Field(..., min_length=2, max_length=200)
    fabric_type: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    occasion: Optional[List[str]] = None
    cost_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Decimal = Field(..., ge=0)
    stock_count: int = Field(default=0, ge=0)
    images: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_published: bool = False
    # Vendor & Batch tracking
    vendor_name: Optional[str] = Field(None, max_length=200)
    batch_number: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[date] = None
    
    @field_validator("selling_price", "cost_price", mode="before")
    @classmethod
    def validate_decimal(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class SareeCreate(SareeBase):
    """Saree creation request"""
    pass


class SareeUpdate(BaseModel):
    """Saree update request (partial)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    fabric_type: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=50)
    occasion: Optional[List[str]] = None
    cost_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    stock_count: Optional[int] = Field(None, ge=0)
    images: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_published: Optional[bool] = None
    # Vendor & Batch tracking
    vendor_name: Optional[str] = Field(None, max_length=200)
    batch_number: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[date] = None


class SareeResponse(SareeBase):
    """Saree response"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SareeListParams(BaseModel):
    """Saree list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    published: Optional[bool] = None
    fabric_type: Optional[str] = None
    color: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    search: Optional[str] = None
