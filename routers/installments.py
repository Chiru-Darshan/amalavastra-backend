"""
Installments Router
Handles installment plan management
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from datetime import date

from database import supabase_admin as supabase
from schemas.installments import (
    InstallmentCreate, InstallmentUpdate, InstallmentResponse,
    InstallmentListParams, InstallmentStatus
)
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.exceptions import ResourceNotFoundError, ValidationError
from core.logging import logger


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[dict])
async def get_installments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_id: Optional[str] = None,
    status: Optional[InstallmentStatus] = None,
    overdue_only: bool = False,
    upcoming_days: Optional[int] = Query(None, ge=1, le=90),
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get all installments with filters and pagination.
    
    **Permissions Required:** payments:read
    """
    query = supabase.table("installment_plan").select("*, orders(customer_id, total_amount)", count="exact")
    
    if order_id:
        query = query.eq("order_id", order_id)
    if status:
        query = query.eq("status", status.value)
    if overdue_only:
        query = query.eq("status", "overdue")
    if upcoming_days:
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=upcoming_days)).date()
        query = query.lte("due_date", future_date.isoformat()).eq("status", "pending")
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order("due_date").range(offset, offset + page_size - 1)
    
    result = query.execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        success=True,
        data=result.data or [],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/order/{order_id}", response_model=DataResponse[list])
async def get_order_installments(
    order_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get installment plan for a specific order.
    
    **Permissions Required:** payments:read
    """
    # Check if order exists
    order = supabase.table("orders").select("id").eq("id", order_id).execute()
    if not order.data:
        raise ResourceNotFoundError("Order", order_id)
    
    installments = supabase.table("installment_plan").select("*").eq("order_id", order_id).order("installment_no").execute()
    
    return DataResponse(
        success=True,
        data=installments.data or []
    )


@router.get("/overdue", response_model=DataResponse[list])
async def get_overdue_installments(
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get all overdue installments.
    
    **Permissions Required:** payments:read
    """
    # Mark overdue installments
    try:
        supabase.rpc("mark_overdue_installments").execute()
    except Exception:
        pass  # Function may not exist
    
    result = supabase.table("overdue_installments").select("*").execute()
    
    return DataResponse(
        success=True,
        data=result.data or []
    )


@router.get("/upcoming", response_model=DataResponse[list])
async def get_upcoming_installments(
    days: int = Query(default=7, ge=1, le=30),
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_READ))
):
    """
    Get upcoming installments due within specified days.
    
    **Permissions Required:** payments:read
    """
    from datetime import datetime, timedelta
    
    future_date = (datetime.now() + timedelta(days=days)).date()
    
    result = supabase.table("installment_plan").select(
        "*, orders(customer_id, customers(name, phone))"
    ).eq("status", "pending").lte("due_date", future_date.isoformat()).order("due_date").execute()
    
    return DataResponse(
        success=True,
        data=result.data or []
    )


@router.post("/", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_installment(
    installment: InstallmentCreate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_CREATE))
):
    """
    Create a new installment.
    
    **Permissions Required:** payments:create
    """
    # Validate order exists
    order = supabase.table("orders").select("id, payment_type").eq("id", installment.order_id).execute()
    if not order.data:
        raise ResourceNotFoundError("Order", installment.order_id)
    
    if order.data[0].get("payment_type") != "installment":
        raise ValidationError("Order is not set for installment payment")
    
    installment_data = installment.model_dump()
    installment_data["expected_amount"] = float(installment_data["expected_amount"])
    installment_data["due_date"] = installment_data["due_date"].isoformat()
    
    result = supabase.table("installment_plan").insert(installment_data).execute()
    
    logger.info(f"Installment created by user {current_user.id} for order {installment.order_id}")
    
    return DataResponse(
        success=True,
        message="Installment created successfully",
        data=result.data[0] if result.data else None
    )


@router.put("/{installment_id}", response_model=DataResponse[dict])
async def update_installment(
    installment_id: str,
    installment: InstallmentUpdate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_CREATE))
):
    """
    Update an installment.
    
    **Permissions Required:** payments:create
    """
    # Check if installment exists
    existing = supabase.table("installment_plan").select("id").eq("id", installment_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Installment", installment_id)
    
    # Filter out None values
    update_data = {k: v for k, v in installment.model_dump().items() if v is not None}
    
    # Handle data conversion
    if update_data.get("expected_amount"):
        update_data["expected_amount"] = float(update_data["expected_amount"])
    if update_data.get("due_date"):
        update_data["due_date"] = update_data["due_date"].isoformat()
    if update_data.get("status"):
        update_data["status"] = update_data["status"].value
    
    result = supabase.table("installment_plan").update(update_data).eq("id", installment_id).execute()
    
    return DataResponse(
        success=True,
        message="Installment updated successfully",
        data=result.data[0] if result.data else None
    )


@router.put("/{installment_id}/mark-paid", response_model=DataResponse[dict])
async def mark_installment_paid(
    installment_id: str,
    paid_amount: Optional[float] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_CREATE))
):
    """
    Mark an installment as paid.
    
    **Permissions Required:** payments:create
    """
    # Check if installment exists
    existing = supabase.table("installment_plan").select("*").eq("id", installment_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Installment", installment_id)
    
    installment = existing.data[0]
    expected_amount = float(installment.get("expected_amount", 0))
    
    update_data = {
        "status": "paid",
        "paid_amount": paid_amount if paid_amount else expected_amount,
        "paid_date": date.today().isoformat()
    }
    
    result = supabase.table("installment_plan").update(update_data).eq("id", installment_id).execute()
    
    logger.info(f"Installment {installment_id} marked as paid by user {current_user.id}")
    
    return DataResponse(
        success=True,
        message="Installment marked as paid",
        data=result.data[0] if result.data else None
    )


@router.delete("/{installment_id}", response_model=MessageResponse)
async def delete_installment(
    installment_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.PAYMENTS_DELETE))
):
    """
    Delete an installment.
    
    **Permissions Required:** payments:delete
    """
    # Check if installment exists
    existing = supabase.table("installment_plan").select("id, status").eq("id", installment_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Installment", installment_id)
    
    if existing.data[0].get("status") == "paid":
        raise ValidationError("Cannot delete a paid installment")
    
    supabase.table("installment_plan").delete().eq("id", installment_id).execute()
    
    logger.info(f"Installment deleted by user {current_user.id}: {installment_id}")
    
    return MessageResponse(
        success=True,
        message="Installment deleted successfully"
    )
