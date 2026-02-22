"""
Orders Router
Handles order management
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from datetime import date

from database import supabase_admin as supabase
from schemas.orders import (
    OrderCreate, OrderUpdate, OrderResponse, OrderListParams,
    OrderStatus, PaymentType
)
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.exceptions import ResourceNotFoundError, ValidationError
from core.logging import logger


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[dict])
async def get_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    customer_id: Optional[str] = None,
    payment_type: Optional[PaymentType] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_READ))
):
    """
    Get all orders with filters and pagination.
    
    **Permissions Required:** orders:read
    """
    # Use orders table with customer join for customer_id filtering
    # since order_summary view doesn't include customer_id
    query = supabase.table("orders").select(
        "*, customers(name, phone), order_items(quantity)",
        count="exact"
    )
    
    if status:
        query = query.eq("status", status.value)
    if customer_id:
        query = query.eq("customer_id", customer_id)
    if payment_type:
        query = query.eq("payment_type", payment_type.value)
    if from_date:
        query = query.gte("created_at", from_date.isoformat())
    if to_date:
        query = query.lte("created_at", to_date.isoformat())
    if search:
        query = query.or_(f"id.ilike.%{search}%")
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
    
    result = query.execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size
    
    # Flatten customer data and calculate item count for frontend compatibility
    orders_data = []
    for order in (result.data or []):
        customer = order.pop("customers", None) or {}
        order_items = order.pop("order_items", None) or []
        order["customer_name"] = customer.get("name", "")
        order["customer_phone"] = customer.get("phone", "")
        order["balance_due"] = float(order.get("total_amount", 0)) - float(order.get("amount_paid", 0))
        # Calculate total quantity from order items
        order["items"] = order_items  # Keep the items for frontend
        orders_data.append(order)
    
    return PaginatedResponse(
        success=True,
        data=orders_data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/{order_id}", response_model=DataResponse[dict])
async def get_order(
    order_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_READ))
):
    """
    Get a specific order by ID with items.
    
    **Permissions Required:** orders:read
    """
    order = supabase.table("orders").select("*").eq("id", order_id).execute().data
    if not order:
        raise ResourceNotFoundError("Order", order_id)
    
    items = supabase.table("order_items").select("*, sarees(name, fabric_type, color)").eq("order_id", order_id).execute().data
    
    # Get customer details
    customer = None
    if order[0].get("customer_id"):
        customer_result = supabase.table("customers").select("name, phone, email").eq("id", order[0]["customer_id"]).execute()
        if customer_result.data:
            customer = customer_result.data[0]
    
    # Get payments
    payments = supabase.table("payments").select("*").eq("order_id", order_id).execute().data
    
    order_data = {
        **order[0],
        "items": items or [],
        "customer": customer,
        "payments": payments or []
    }
    
    return DataResponse(success=True, data=order_data)


@router.post("/", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_CREATE))
):
    """
    Create a new order.
    
    **Permissions Required:** orders:create
    """
    from datetime import datetime, timedelta
    
    # Validate customer exists if provided
    if order.customer_id:
        customer = supabase.table("customers").select("id").eq("id", order.customer_id).execute()
        if not customer.data:
            raise ValidationError(f"Customer {order.customer_id} not found")
    
    # Prepare order data
    order_data = order.model_dump(exclude={"items"})
    order_data["status"] = order.status.value if hasattr(order.status, 'value') else order.status
    order_data["payment_type"] = order.payment_type.value if hasattr(order.payment_type, 'value') else order.payment_type
    order_data["total_amount"] = float(order.total_amount)
    # Note: created_by not in DB schema
    
    # Convert dates
    if order_data.get("due_date"):
        order_data["due_date"] = order_data["due_date"].isoformat()
    if order_data.get("delivery_date"):
        order_data["delivery_date"] = order_data["delivery_date"].isoformat()
    
    created_order = supabase.table("orders").insert(order_data).execute().data[0]
    
    # Create order items
    for item in order.items:
        item_data = item.model_dump()
        item_data["order_id"] = created_order["id"]
        item_data["unit_price"] = float(item_data["unit_price"])
        item_data["discount"] = float(item_data.get("discount", 0))
        supabase.table("order_items").insert(item_data).execute()
        
        # Update stock count
        supabase.rpc("decrement_stock", {
            "saree_id": item.saree_id,
            "qty": item.quantity
        }).execute()
    
    # Create installment plan if payment_type is installment
    if order.payment_type == PaymentType.INSTALLMENT and order.installment_count:
        installment_amount = float(order.total_amount) / order.installment_count
        today = datetime.now().date()
        
        for i in range(order.installment_count):
            due_date = today + timedelta(days=30 * (i + 1))  # Monthly installments
            installment_data = {
                "order_id": created_order["id"],
                "installment_no": i + 1,
                "expected_amount": round(installment_amount, 2),
                "due_date": due_date.isoformat(),
                "status": "pending"
            }
            supabase.table("installment_plan").insert(installment_data).execute()
        
        logger.info(f"Created {order.installment_count} installments for order {created_order['id']}")
    
    logger.info(f"Order created by user {current_user.id}: {created_order['id']}")
    
    return DataResponse(
        success=True,
        message="Order created successfully",
        data=created_order
    )


@router.put("/{order_id}", response_model=DataResponse[dict])
async def update_order(
    order_id: str,
    order: OrderUpdate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_UPDATE))
):
    """
    Update an existing order.
    
    **Permissions Required:** orders:update
    """
    # Check if order exists
    existing = supabase.table("orders").select("id, status").eq("id", order_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Order", order_id)
    
    # Filter out None values
    update_data = {k: v for k, v in order.model_dump().items() if v is not None}
    
    # Handle enum values
    if update_data.get("status"):
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], 'value') else update_data["status"]
    
    # Convert dates
    if update_data.get("delivery_date"):
        update_data["delivery_date"] = update_data["delivery_date"].isoformat()
    
    result = supabase.table("orders").update(update_data).eq("id", order_id).execute()
    
    return DataResponse(
        success=True,
        message="Order updated successfully",
        data=result.data[0] if result.data else None
    )


@router.put("/{order_id}/status", response_model=DataResponse[dict])
async def update_order_status(
    order_id: str,
    status: OrderStatus = Query(...),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_UPDATE))
):
    """
    Update order status.
    
    **Permissions Required:** orders:update
    """
    # Check if order exists
    existing = supabase.table("orders").select("id").eq("id", order_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Order", order_id)
    
    result = supabase.table("orders").update({"status": status.value}).eq("id", order_id).execute()
    
    logger.info(f"Order {order_id} status changed to {status.value} by user {current_user.id}")
    
    return DataResponse(
        success=True,
        message=f"Order status updated to {status.value}",
        data=result.data[0] if result.data else None
    )


@router.delete("/{order_id}", response_model=MessageResponse)
async def delete_order(
    order_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ORDERS_DELETE))
):
    """
    Delete an order.
    
    **Permissions Required:** orders:delete
    """
    # Check if order exists
    existing = supabase.table("orders").select("id").eq("id", order_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Order", order_id)
    
    # Delete order items first
    supabase.table("order_items").delete().eq("order_id", order_id).execute()
    
    # Delete payments
    supabase.table("payments").delete().eq("order_id", order_id).execute()
    
    # Delete order
    supabase.table("orders").delete().eq("id", order_id).execute()
    
    logger.info(f"Order deleted by user {current_user.id}: {order_id}")
    
    return MessageResponse(
        success=True,
        message="Order deleted successfully"
    )
