from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

class SareeCreate(BaseModel):
    name: str
    fabric_type: Optional[str] = None
    color: Optional[str] = None
    occasion: Optional[List[str]] = None
    cost_price: Optional[Decimal] = None
    selling_price: Decimal
    stock_count: int = 0
    images: Optional[List[str]] = None
    description: Optional[str] = None
    is_published: bool = False

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: Optional[str] = None
    status: str = "pending"
    payment_type: str = "full"
    total_amount: Decimal
    installment_count: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    delivery_date: Optional[date] = None
    items: List[dict]

class PaymentCreate(BaseModel):
    order_id: str
    amount: Decimal
    method: str
    reference_no: Optional[str] = None
    notes: Optional[str] = None

class InstallmentCreate(BaseModel):
    order_id: str
    installment_no: int
    due_date: date
    expected_amount: Decimal
