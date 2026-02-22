"""
Customers Router
Handles customer management
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from database import supabase_admin as supabase
from schemas.customers import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListParams
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.exceptions import ResourceNotFoundError
from core.logging import logger


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[dict])
async def get_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_READ))
):
    """
    Get all customers with pagination.
    
    **Permissions Required:** customers:read
    """
    query = supabase.table("customers").select("*", count="exact")
    
    if search:
        query = query.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%,email.ilike.%{search}%")
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
    
    result = query.execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size
    
    # Add order count and total spent for each customer
    customers_data = []
    for customer in (result.data or []):
        # Get order count and total spent
        orders = supabase.table("orders").select("total_amount").eq("customer_id", customer["id"]).neq("status", "cancelled").execute()
        customer["order_count"] = len(orders.data or [])
        customer["total_spent"] = sum(float(o.get("total_amount", 0)) for o in (orders.data or []))
        customers_data.append(customer)
    
    return PaginatedResponse(
        success=True,
        data=customers_data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/{customer_id}", response_model=DataResponse[dict])
async def get_customer(
    customer_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_READ))
):
    """
    Get a specific customer by ID.
    
    **Permissions Required:** customers:read
    """
    data = supabase.table("customers").select("*").eq("id", customer_id).execute().data
    if not data:
        raise ResourceNotFoundError("Customer", customer_id)
    
    return DataResponse(success=True, data=data[0])


@router.get("/{customer_id}/orders", response_model=DataResponse[list])
async def get_customer_orders(
    customer_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_READ))
):
    """
    Get all orders for a specific customer.
    
    **Permissions Required:** customers:read
    """
    # Check if customer exists
    customer = supabase.table("customers").select("id").eq("id", customer_id).execute()
    if not customer.data:
        raise ResourceNotFoundError("Customer", customer_id)
    
    orders = supabase.table("orders").select("*").eq("customer_id", customer_id).order("created_at", desc=True).execute()
    
    return DataResponse(success=True, data=orders.data or [])


@router.post("/", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_CREATE))
):
    """
    Create a new customer.
    
    **Permissions Required:** customers:create
    """
    result = supabase.table("customers").insert(customer.model_dump()).execute()
    
    logger.info(f"Customer created by user {current_user.id}: {customer.name}")
    
    return DataResponse(
        success=True,
        message="Customer created successfully",
        data=result.data[0] if result.data else None
    )


@router.put("/{customer_id}", response_model=DataResponse[dict])
async def update_customer(
    customer_id: str,
    customer: CustomerUpdate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_UPDATE))
):
    """
    Update an existing customer.
    
    **Permissions Required:** customers:update
    """
    # Check if customer exists
    existing = supabase.table("customers").select("id").eq("id", customer_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Customer", customer_id)
    
    # Filter out None values
    update_data = {k: v for k, v in customer.model_dump().items() if v is not None}
    
    result = supabase.table("customers").update(update_data).eq("id", customer_id).execute()
    
    return DataResponse(
        success=True,
        message="Customer updated successfully",
        data=result.data[0] if result.data else None
    )


@router.delete("/{customer_id}", response_model=MessageResponse)
async def delete_customer(
    customer_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.CUSTOMERS_DELETE))
):
    """
    Delete a customer.
    
    **Permissions Required:** customers:delete
    """
    # Check if customer exists
    existing = supabase.table("customers").select("id").eq("id", customer_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Customer", customer_id)
    
    supabase.table("customers").delete().eq("id", customer_id).execute()
    
    logger.info(f"Customer deleted by user {current_user.id}: {customer_id}")
    
    return MessageResponse(
        success=True,
        message="Customer deleted successfully"
    )
