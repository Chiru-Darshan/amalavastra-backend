"""
Customer Schemas
Request and response models for customer endpoints
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class CustomerBase(BaseModel):
    """Base customer schema"""
    name: str = Field(..., min_length=2, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            # Remove spaces and dashes for validation
            cleaned = re.sub(r"[\s\-]", "", v)
            if not re.match(r"^\+?[1-9]\d{6,14}$", cleaned):
                raise ValueError("Invalid phone number format")
        return v


class CustomerCreate(CustomerBase):
    """Customer creation request"""
    pass


class CustomerUpdate(BaseModel):
    """Customer update request (partial)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)


class CustomerResponse(CustomerBase):
    """Customer response"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    total_orders: Optional[int] = 0
    total_spent: Optional[float] = 0.0
    
    class Config:
        from_attributes = True


class CustomerListParams(BaseModel):
    """Customer list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
