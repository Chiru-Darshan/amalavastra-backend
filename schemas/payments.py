"""
Payment Schemas
Request and response models for payment endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class PaymentBase(BaseModel):
    """Base payment schema"""
    order_id: str
    amount: Decimal = Field(..., gt=0)
    method: PaymentMethod
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator("amount", mode="before")
    @classmethod
    def validate_decimal(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class PaymentCreate(PaymentBase):
    """Payment creation request"""
    pass


class PaymentResponse(PaymentBase):
    """Payment response"""
    id: str
    created_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaymentListParams(BaseModel):
    """Payment list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    order_id: Optional[str] = None
    method: Optional[PaymentMethod] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
