"""
Payments Router
Handles payment management
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from datetime import datetime, date, timedelta

from database import supabase_admin as supabase
from schemas.payments import PaymentCreate, PaymentResponse, PaymentListParams, PaymentMethod
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.exceptions import ResourceNotFoundError, ValidationError
from core.logging import logger


router = APIRouter()


@router.get("/summary", response_model=DataResponse[dict])
async def get_payment_summary(
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get payment summary statistics.
    
    **Permissions Required:** payments:read
    """
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # Today's payments
    today_payments = supabase.table("payments").select("amount").gte(
        "paid_at", today.isoformat()
    ).execute()
    today_total = sum(float(p.get("amount", 0)) for p in (today_payments.data or []))
    
    # This week's payments
    week_payments = supabase.table("payments").select("amount").gte(
        "paid_at", start_of_week.isoformat()
    ).execute()
    week_total = sum(float(p.get("amount", 0)) for p in (week_payments.data or []))
    
    # This month's payments
    month_payments = supabase.table("payments").select("amount").gte(
        "paid_at", start_of_month.isoformat()
    ).execute()
    month_total = sum(float(p.get("amount", 0)) for p in (month_payments.data or []))
    
    # Pending dues (orders total - payments total)
    orders = supabase.table("orders").select("total_amount").neq("status", "cancelled").execute()
    total_order_value = sum(float(o.get("total_amount", 0)) for o in (orders.data or []))
    
    all_payments = supabase.table("payments").select("amount").execute()
    total_paid = sum(float(p.get("amount", 0)) for p in (all_payments.data or []))
    
    pending_dues = max(0, total_order_value - total_paid)
    
    return DataResponse(
        success=True,
        data={
            "today": today_total,
            "this_week": week_total,
            "this_month": month_total,
            "pending_dues": pending_dues
        }
    )


@router.get("/", response_model=PaginatedResponse[dict])
async def get_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_id: Optional[str] = None,
    method: Optional[PaymentMethod] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get all payments with filters and pagination.
    
    **Permissions Required:** payments:read
    """
    query = supabase.table("payments").select(
        "*, orders(id, customer_id, total_amount, customers(name))",
        count="exact"
    )
    
    if order_id:
        query = query.eq("order_id", order_id)
    if method:
        query = query.eq("method", method.value)
    if from_date:
        query = query.gte("paid_at", from_date.isoformat())
    if to_date:
        query = query.lte("paid_at", to_date.isoformat())
    if search:
        query = query.or_(f"order_id.ilike.%{search}%,reference_no.ilike.%{search}%")
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order("paid_at", desc=True).range(offset, offset + page_size - 1)
    
    result = query.execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size
    
    # Flatten customer data for frontend compatibility
    payments_data = []
    for payment in (result.data or []):
        order = payment.pop("orders", None) or {}
        customers = order.get("customers", None) or {}
        payment["customer_name"] = customers.get("name", "")
        payments_data.append(payment)
    
    return PaginatedResponse(
        success=True,
        data=payments_data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/order/{order_id}", response_model=DataResponse[list])
async def get_order_payments(
    order_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get all payments for a specific order.
    
    **Permissions Required:** payments:read
    """
    # Check if order exists
    order = supabase.table("orders").select("id, total_amount").eq("id", order_id).execute()
    if not order.data:
        raise ResourceNotFoundError("Order", order_id)
    
    payments = supabase.table("payments").select("*").eq("order_id", order_id).order("paid_at", desc=True).execute()
    
    # Calculate totals
    total_paid = sum(float(p.get("amount", 0)) for p in (payments.data or []))
    total_amount = float(order.data[0].get("total_amount", 0))
    
    return DataResponse(
        success=True,
        data={
            "payments": payments.data or [],
            "total_paid": total_paid,
            "total_amount": total_amount,
            "balance": total_amount - total_paid
        }
    )


@router.post("/", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_CREATE))
):
    """
    Record a new payment.
    
    **Permissions Required:** payments:create
    """
    # Validate order exists
    order = supabase.table("orders").select("id, total_amount").eq("id", payment.order_id).execute()
    if not order.data:
        raise ResourceNotFoundError("Order", payment.order_id)
    
    # Check if payment doesn't exceed remaining balance
    existing_payments = supabase.table("payments").select("amount").eq("order_id", payment.order_id).execute()
    total_paid = sum(float(p.get("amount", 0)) for p in (existing_payments.data or []))
    total_amount = float(order.data[0].get("total_amount", 0))
    
    if total_paid + float(payment.amount) > total_amount:
        raise ValidationError(f"Payment amount exceeds remaining balance of {total_amount - total_paid}")
    
    # Create payment
    payment_data = payment.model_dump()
    payment_data["amount"] = float(payment_data["amount"])
    payment_data["method"] = payment_data["method"].value if hasattr(payment_data["method"], 'value') else payment_data["method"]
    # Note: created_by not in DB schema, skip it
    
    result = supabase.table("payments").insert(payment_data).execute()
    
    # Update order status if fully paid
    new_total_paid = total_paid + float(payment.amount)
    if new_total_paid >= total_amount:
        supabase.table("orders").update({"status": "delivered"}).eq("id", payment.order_id).execute()
    
    logger.info(f"Payment recorded by user {current_user.id}: {payment.amount} for order {payment.order_id}")
    
    return DataResponse(
        success=True,
        message="Payment recorded successfully",
        data=result.data[0] if result.data else None
    )


@router.delete("/{payment_id}", response_model=MessageResponse)
async def delete_payment(
    payment_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_DELETE))
):
    """
    Delete a payment record.
    
    **Permissions Required:** payments:delete
    """
    # Check if payment exists
    existing = supabase.table("payments").select("id").eq("id", payment_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Payment", payment_id)
    
    supabase.table("payments").delete().eq("id", payment_id).execute()
    
    logger.info(f"Payment deleted by user {current_user.id}: {payment_id}")
    
    return MessageResponse(
        success=True,
        message="Payment deleted successfully"
    )
