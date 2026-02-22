"""
Invoice Service
Business logic for invoice generation and management
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from database import supabase_admin as supabase
from core.config import settings
from core.exceptions import ResourceNotFoundError, ValidationError
from schemas.invoices import (
    InvoiceCreate, InvoiceResponse, InvoiceStatus,
    InvoiceItemSchema, InvoiceGenerateFromOrder
)
from core.logging import logger


class InvoiceService:
    """Service for invoice management"""
    
    @staticmethod
    def generate_invoice_number() -> str:
        """Generate a unique invoice number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:6].upper()
        return f"{settings.INVOICE_PREFIX}-{timestamp}-{unique_id}"
    
    @staticmethod
    async def create_invoice_from_order(
        order_id: str,
        tax_rate: Decimal = Decimal("18"),
        discount_percent: Decimal = Decimal("0"),
        notes: Optional[str] = None,
        terms: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an invoice from an existing order
        """
        # Fetch order details
        order_result = supabase.table("orders").select("*").eq("id", order_id).execute()
        if not order_result.data:
            raise ResourceNotFoundError("Order", order_id)
        
        order = order_result.data[0]
        
        # Fetch order items
        items_result = supabase.table("order_items").select(
            "*, sarees(name, fabric_type)"
        ).eq("order_id", order_id).execute()
        items = items_result.data or []
        
        # Fetch customer details
        customer = None
        if order.get("customer_id"):
            customer_result = supabase.table("customers").select("*").eq(
                "id", order["customer_id"]
            ).execute()
            if customer_result.data:
                customer = customer_result.data[0]
        
        # Calculate amounts
        subtotal = Decimal("0")
        invoice_items = []
        
        for item in items:
            saree = item.get("sarees", {}) or {}
            quantity = item.get("quantity", 1)
            unit_price = Decimal(str(item.get("unit_price", 0)))
            item_discount = Decimal(str(item.get("discount", 0)))
            
            item_subtotal = (quantity * unit_price) - item_discount
            item_tax = item_subtotal * (tax_rate / 100)
            
            invoice_items.append({
                "description": saree.get("name", "Saree"),
                "hsn_code": "5007",  # HSN code for silk fabrics
                "quantity": quantity,
                "unit_price": float(unit_price),
                "discount_percent": float((item_discount / (quantity * unit_price)) * 100) if quantity * unit_price > 0 else 0,
                "tax_percent": float(tax_rate),
                "subtotal": float(item_subtotal),
                "tax_amount": float(item_tax),
                "total": float(item_subtotal + item_tax)
            })
            
            subtotal += item_subtotal
        
        # Apply overall discount
        discount_amount = subtotal * (discount_percent / 100)
        taxable_amount = subtotal - discount_amount
        tax_amount = taxable_amount * (tax_rate / 100)
        total_amount = taxable_amount + tax_amount
        
        # Get paid amount from payments
        payments_result = supabase.table("payments").select("amount").eq(
            "order_id", order_id
        ).execute()
        paid_amount = sum(Decimal(str(p.get("amount", 0))) for p in (payments_result.data or []))
        due_amount = total_amount - paid_amount
        
        # Determine status
        if paid_amount >= total_amount:
            status = InvoiceStatus.PAID.value
        elif paid_amount > 0:
            status = InvoiceStatus.PARTIALLY_PAID.value
        else:
            status = InvoiceStatus.ISSUED.value
        
        # Default terms if not provided
        if not terms:
            terms = (
                "1. Payment is due within 30 days of invoice date.\n"
                "2. All items are subject to quality inspection.\n"
                "3. Returns accepted within 7 days of delivery with original tags.\n"
                "4. GST as applicable."
            )
        
        # Create invoice record
        invoice_data = {
            "id": str(uuid.uuid4()),
            "invoice_number": InvoiceService.generate_invoice_number(),
            "order_id": order_id,
            "customer_id": order.get("customer_id"),
            "customer_name": customer.get("name") if customer else "Walk-in Customer",
            "customer_address": customer.get("address") if customer else None,
            "customer_phone": customer.get("phone") if customer else None,
            "customer_email": customer.get("email") if customer else None,
            "company_name": settings.COMPANY_NAME,
            "company_address": settings.COMPANY_ADDRESS,
            "company_phone": settings.COMPANY_PHONE,
            "company_email": settings.COMPANY_EMAIL,
            "company_gst": settings.COMPANY_GST,
            "items": invoice_items,
            "subtotal": float(subtotal),
            "discount_amount": float(discount_amount),
            "tax_amount": float(tax_amount),
            "total_amount": float(total_amount),
            "paid_amount": float(paid_amount),
            "due_amount": float(due_amount),
            "status": status,
            "issue_date": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).date().isoformat() if due_amount > 0 else None,
            "notes": notes,
            "terms": terms,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("invoices").insert(invoice_data).execute()
        
        logger.info(f"Created invoice {invoice_data['invoice_number']} for order {order_id}")
        
        return invoice_data
    
    @staticmethod
    async def get_invoice(invoice_id: str) -> Dict[str, Any]:
        """Get invoice by ID"""
        result = supabase.table("invoices").select("*").eq("id", invoice_id).execute()
        if not result.data:
            raise ResourceNotFoundError("Invoice", invoice_id)
        return result.data[0]
    
    @staticmethod
    async def get_invoice_by_number(invoice_number: str) -> Dict[str, Any]:
        """Get invoice by invoice number"""
        result = supabase.table("invoices").select("*").eq(
            "invoice_number", invoice_number
        ).execute()
        if not result.data:
            raise ResourceNotFoundError("Invoice", invoice_number)
        return result.data[0]
    
    @staticmethod
    async def list_invoices(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """List invoices with filters and pagination"""
        query = supabase.table("invoices").select("*", count="exact")
        
        if status:
            query = query.eq("status", status)
        if customer_id:
            query = query.eq("customer_id", customer_id)
        if from_date:
            query = query.gte("issue_date", from_date.isoformat())
        if to_date:
            query = query.lte("issue_date", to_date.isoformat())
        
        # Pagination
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        
        result = query.execute()
        total = result.count or 0
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "data": result.data or [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    
    @staticmethod
    async def update_invoice_status(
        invoice_id: str,
        status: InvoiceStatus
    ) -> Dict[str, Any]:
        """Update invoice status"""
        result = supabase.table("invoices").update({
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", invoice_id).execute()
        
        if not result.data:
            raise ResourceNotFoundError("Invoice", invoice_id)
        
        return result.data[0]
    
    @staticmethod
    async def cancel_invoice(invoice_id: str, reason: str = None) -> Dict[str, Any]:
        """Cancel an invoice"""
        invoice = await InvoiceService.get_invoice(invoice_id)
        
        if invoice.get("status") == InvoiceStatus.PAID.value:
            raise ValidationError("Cannot cancel a paid invoice")
        
        result = supabase.table("invoices").update({
            "status": InvoiceStatus.CANCELLED.value,
            "notes": f"{invoice.get('notes', '')}\n\nCancelled: {reason}" if reason else invoice.get('notes'),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", invoice_id).execute()
        
        return result.data[0]
