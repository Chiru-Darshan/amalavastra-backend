"""
Invoice Schemas
Request and response models for invoice generation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceItemSchema(BaseModel):
    """Invoice item schema"""
    description: str
    hsn_code: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    
    @property
    def subtotal(self) -> Decimal:
        base = self.quantity * self.unit_price
        discount = base * (self.discount_percent / 100)
        return base - discount
    
    @property
    def tax_amount(self) -> Decimal:
        return self.subtotal * (self.tax_percent / 100)
    
    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax_amount


class InvoiceCreate(BaseModel):
    """Invoice creation request"""
    order_id: str
    notes: Optional[str] = Field(None, max_length=1000)
    terms: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[date] = None


class InvoiceGenerateFromOrder(BaseModel):
    """Generate invoice from order"""
    order_id: str
    include_tax: bool = True
    tax_rate: Decimal = Field(default=Decimal("18"), ge=0, le=100)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Invoice response"""
    id: str
    invoice_number: str
    order_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    
    # Company details
    company_name: str
    company_address: str
    company_phone: str
    company_email: str
    company_gst: str
    
    # Items
    items: List[InvoiceItemSchema] = []
    
    # Amounts
    subtotal: Decimal
    discount_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal
    paid_amount: Decimal = Decimal("0")
    due_amount: Decimal = Decimal("0")
    
    # Metadata
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: datetime
    due_date: Optional[date] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InvoiceListParams(BaseModel):
    """Invoice list query parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[InvoiceStatus] = None
    customer_id: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    search: Optional[str] = None


class InvoicePDFRequest(BaseModel):
    """Request for PDF generation"""
    invoice_id: str
    send_email: bool = False
    email_to: Optional[str] = None
