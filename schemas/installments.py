"""
Installment Schemas
Request and response models for installment endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class InstallmentStatus(str, Enum):
    """Installment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class InstallmentBase(BaseModel):
    """Base installment schema"""
    order_id: str
    installment_no: int = Field(..., ge=1)
    due_date: date
    expected_amount: Decimal = Field(..., gt=0)
    
    @field_validator("expected_amount", mode="before")
    @classmethod
    def validate_decimal(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class InstallmentCreate(InstallmentBase):
    """Installment creation request"""
    pass


class InstallmentUpdate(BaseModel):
    """Installment update request"""
    due_date: Optional[date] = None
    expected_amount: Optional[Decimal] = Field(None, gt=0)
    status: Optional[InstallmentStatus] = None


class InstallmentResponse(InstallmentBase):
    """Installment response"""
    id: str
    status: InstallmentStatus = InstallmentStatus.PENDING
    paid_amount: Decimal = Decimal("0")
    paid_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InstallmentListParams(BaseModel):
    """Installment list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    order_id: Optional[str] = None
    status: Optional[InstallmentStatus] = None
    overdue_only: bool = False
    upcoming_days: Optional[int] = Field(None, ge=1, le=90)
