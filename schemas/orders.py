"""
Order Schemas
Request and response models for order endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentType(str, Enum):
    """Payment type enumeration"""
    FULL = "full"
    INSTALLMENT = "installment"
    PARTIAL = "partial"


class OrderItemBase(BaseModel):
    """Base order item schema"""
    saree_id: str
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    
    @field_validator("unit_price", "discount", mode="before")
    @classmethod
    def validate_decimal(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class OrderItemCreate(OrderItemBase):
    """Order item creation request"""
    pass


class OrderItemResponse(OrderItemBase):
    """Order item response"""
    id: str
    order_id: str
    saree_name: Optional[str] = None
    subtotal: Decimal
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Base order schema"""
    customer_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    payment_type: PaymentType = PaymentType.FULL
    total_amount: Decimal = Field(..., ge=0)
    installment_count: Optional[int] = Field(None, ge=1, le=24)
    due_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)
    delivery_date: Optional[date] = None
    
    @field_validator("total_amount", mode="before")
    @classmethod
    def validate_decimal(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class OrderCreate(OrderBase):
    """Order creation request"""
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    """Order update request (partial)"""
    customer_id: Optional[str] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = Field(None, max_length=2000)
    delivery_date: Optional[date] = None


class OrderResponse(OrderBase):
    """Order response"""
    id: str
    order_number: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[OrderItemResponse] = []
    paid_amount: Decimal = Decimal("0")
    pending_amount: Decimal = Decimal("0")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrderListParams(BaseModel):
    """Order list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[OrderStatus] = None
    customer_id: Optional[str] = None
    payment_type: Optional[PaymentType] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    search: Optional[str] = None
