"""
Analytics Router
Handles business analytics and reporting
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import date, datetime, timedelta

from database import supabase_admin as supabase
from schemas.base import DataResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.logging import logger


router = APIRouter()


@router.get("/dashboard", response_model=DataResponse[dict])
async def get_dashboard_stats(
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get dashboard statistics summary.
    
    **Permissions Required:** analytics:read
    """
    # Get counts
    total_orders = supabase.table("orders").select("*", count="exact").execute().count or 0
    pending_orders = supabase.table("orders").select("*", count="exact").eq("status", "pending").execute().count or 0
    
    try:
        overdue = supabase.table("overdue_installments").select("*", count="exact").execute().count or 0
    except Exception:
        overdue = 0
    
    try:
        low_stock = supabase.table("low_stock_sarees").select("*", count="exact").execute().count or 0
    except Exception:
        low_stock = supabase.table("sarees").select("*", count="exact").lt("stock_count", 5).execute().count or 0
    
    # Calculate revenue for current month
    start_of_month = date.today().replace(day=1)
    monthly_revenue_result = supabase.table("payments").select("amount").gte(
        "paid_at", start_of_month.isoformat()
    ).execute()
    monthly_revenue = sum(float(p.get("amount", 0)) for p in (monthly_revenue_result.data or []))
    
    # Get total customers
    total_customers = supabase.table("customers").select("*", count="exact").execute().count or 0
    
    # Get total sarees
    total_sarees = supabase.table("sarees").select("*", count="exact").execute().count or 0
    
    return DataResponse(
        success=True,
        data={
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "overdue_installments": overdue,
            "low_stock_items": low_stock,
            "monthly_revenue": monthly_revenue,
            "total_customers": total_customers,
            "total_sarees": total_sarees
        }
    )


@router.get("/low-stock", response_model=DataResponse[list])
async def get_low_stock(
    threshold: int = Query(default=5, ge=1, le=50),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get sarees with low stock.
    
    **Permissions Required:** analytics:read
    """
    try:
        result = supabase.table("low_stock_sarees").select("*").execute()
    except Exception:
        # Fallback if view doesn't exist
        result = supabase.table("sarees").select("*").lt("stock_count", threshold).execute()
    
    return DataResponse(
        success=True,
        data=result.data or []
    )


@router.get("/monthly-revenue", response_model=DataResponse[list])
async def get_monthly_revenue(
    months: int = Query(default=12, ge=1, le=24),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get monthly revenue breakdown.
    
    **Permissions Required:** analytics:read
    """
    try:
        result = supabase.table("monthly_revenue").select("*").limit(months).execute()
        return DataResponse(success=True, data=result.data or [])
    except Exception:
        # Calculate manually if view doesn't exist
        from_date = (date.today() - timedelta(days=365)).isoformat()
        payments = supabase.table("payments").select("amount, paid_at").gte("paid_at", from_date).execute()
        
        # Group by month
        monthly = {}
        for p in (payments.data or []):
            month_key = p.get("paid_at", "")[:7]  # YYYY-MM format
            if month_key:
                monthly[month_key] = monthly.get(month_key, 0) + float(p.get("amount", 0))
        
        revenue_data = [{"month": k, "revenue": v} for k, v in sorted(monthly.items(), reverse=True)]
        
        return DataResponse(success=True, data=revenue_data[:months])


@router.get("/sales-by-category", response_model=DataResponse[list])
async def get_sales_by_category(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get sales breakdown by fabric type/category.
    
    **Permissions Required:** analytics:read
    """
    query = supabase.table("order_items").select("quantity, unit_price, sarees(fabric_type)")
    
    if from_date:
        query = query.gte("created_at", from_date.isoformat())
    if to_date:
        query = query.lte("created_at", to_date.isoformat())
    
    result = query.execute()
    
    # Group by fabric type
    categories = {}
    for item in (result.data or []):
        fabric = item.get("sarees", {}).get("fabric_type", "Other") or "Other"
        qty = item.get("quantity", 1)
        price = float(item.get("unit_price", 0))
        
        if fabric not in categories:
            categories[fabric] = {"count": 0, "revenue": 0}
        
        categories[fabric]["count"] += qty
        categories[fabric]["revenue"] += qty * price
    
    data = [
        {"category": k, "items_sold": v["count"], "revenue": v["revenue"]}
        for k, v in categories.items()
    ]
    
    return DataResponse(
        success=True,
        data=sorted(data, key=lambda x: x["revenue"], reverse=True)
    )


@router.get("/top-customers", response_model=DataResponse[list])
async def get_top_customers(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get top customers by total spending.
    
    **Permissions Required:** analytics:read
    """
    # Get all orders with customer info
    orders = supabase.table("orders").select(
        "customer_id, total_amount, customers(name, phone)"
    ).not_.is_("customer_id", "null").execute()
    
    # Aggregate by customer
    customers = {}
    for order in (orders.data or []):
        customer_id = order.get("customer_id")
        if not customer_id:
            continue
        
        if customer_id not in customers:
            customer = order.get("customers", {})
            customers[customer_id] = {
                "customer_id": customer_id,
                "name": customer.get("name", "Unknown"),
                "phone": customer.get("phone"),
                "total_orders": 0,
                "total_spent": 0
            }
        
        customers[customer_id]["total_orders"] += 1
        customers[customer_id]["total_spent"] += float(order.get("total_amount", 0))
    
    # Sort and limit
    top_customers = sorted(
        customers.values(),
        key=lambda x: x["total_spent"],
        reverse=True
    )[:limit]
    
    return DataResponse(success=True, data=top_customers)


@router.get("/sales-trend", response_model=DataResponse[list])
async def get_sales_trend(
    days: int = Query(default=30, ge=7, le=90),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get daily sales trend for the specified number of days.
    
    **Permissions Required:** analytics:read
    """
    from_date = (date.today() - timedelta(days=days)).isoformat()
    
    payments = supabase.table("payments").select("amount, paid_at").gte(
        "paid_at", from_date
    ).order("paid_at").execute()
    
    # Group by day
    daily = {}
    for p in (payments.data or []):
        day_key = p.get("paid_at", "")[:10]  # YYYY-MM-DD format
        if day_key:
            daily[day_key] = daily.get(day_key, 0) + float(p.get("amount", 0))
    
    # Fill in missing days
    trend_data = []
    current = date.today() - timedelta(days=days)
    while current <= date.today():
        day_str = current.isoformat()
        trend_data.append({
            "date": day_str,
            "revenue": daily.get(day_str, 0)
        })
        current += timedelta(days=1)
    
    return DataResponse(success=True, data=trend_data)


@router.get("/order-status-summary", response_model=DataResponse[dict])
async def get_order_status_summary(
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get summary of orders by status.
    
    **Permissions Required:** analytics:read
    """
    statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"]
    
    summary = {}
    for status in statuses:
        count = supabase.table("orders").select("*", count="exact").eq("status", status).execute().count or 0
        summary[status] = count
    
    return DataResponse(success=True, data=summary)


@router.get("/stats", response_model=DataResponse[dict])
async def get_analytics_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get comprehensive analytics statistics.
    
    **Permissions Required:** analytics:read
    """
    from_date = (date.today() - timedelta(days=days)).isoformat()
    prev_from_date = (date.today() - timedelta(days=days * 2)).isoformat()
    prev_to_date = from_date
    
    # Current period revenue
    current_payments = supabase.table("payments").select("amount").gte("paid_at", from_date).execute()
    total_revenue = sum(float(p.get("amount", 0)) for p in (current_payments.data or []))
    
    # Previous period revenue for growth calculation
    prev_payments = supabase.table("payments").select("amount").gte(
        "paid_at", prev_from_date
    ).lt("paid_at", prev_to_date).execute()
    prev_revenue = sum(float(p.get("amount", 0)) for p in (prev_payments.data or []))
    
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    # Current period orders
    current_orders = supabase.table("orders").select("*", count="exact").gte("created_at", from_date).execute()
    total_orders = current_orders.count or 0
    
    # Previous period orders
    prev_orders = supabase.table("orders").select("*", count="exact").gte(
        "created_at", prev_from_date
    ).lt("created_at", prev_to_date).execute()
    prev_order_count = prev_orders.count or 0
    
    orders_growth = ((total_orders - prev_order_count) / prev_order_count * 100) if prev_order_count > 0 else 0
    
    # New customers in period
    new_customers = supabase.table("customers").select("*", count="exact").gte("created_at", from_date).execute()
    new_customer_count = new_customers.count or 0
    
    prev_new_customers = supabase.table("customers").select("*", count="exact").gte(
        "created_at", prev_from_date
    ).lt("created_at", prev_to_date).execute()
    prev_new_customer_count = prev_new_customers.count or 0
    
    customers_growth = ((new_customer_count - prev_new_customer_count) / prev_new_customer_count * 100) if prev_new_customer_count > 0 else 0
    
    # Average order value
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    prev_avg = prev_revenue / prev_order_count if prev_order_count > 0 else 0
    aov_growth = ((avg_order_value - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0
    
    # Total customers
    total_customers = supabase.table("customers").select("*", count="exact").execute().count or 0
    
    # Repeat customers (customers with more than 1 order)
    orders_by_customer = supabase.table("orders").select("customer_id").execute()
    customer_order_counts = {}
    for order in (orders_by_customer.data or []):
        cid = order.get("customer_id")
        if cid:
            customer_order_counts[cid] = customer_order_counts.get(cid, 0) + 1
    repeat_customers = sum(1 for count in customer_order_counts.values() if count > 1)
    
    # Collection rate
    all_orders = supabase.table("orders").select("total_amount").neq("status", "cancelled").execute()
    total_order_value = sum(float(o.get("total_amount", 0)) for o in (all_orders.data or []))
    
    all_payments = supabase.table("payments").select("amount").execute()
    total_paid = sum(float(p.get("amount", 0)) for p in (all_payments.data or []))
    
    collection_rate = (total_paid / total_order_value * 100) if total_order_value > 0 else 100
    outstanding_amount = max(0, total_order_value - total_paid)
    
    # Payment methods breakdown
    payment_methods = {}
    for p in (all_payments.data or []):
        method = p.get("method", "other")
        payment_methods[method] = payment_methods.get(method, 0) + float(p.get("amount", 0))
    
    payment_method_list = [{"method": k, "amount": v} for k, v in payment_methods.items()]
    
    # Top products
    order_items = supabase.table("order_items").select(
        "saree_id, quantity, unit_price, sarees(name, fabric_type)"
    ).execute()
    
    product_sales = {}
    for item in (order_items.data or []):
        saree_id = item.get("saree_id")
        if saree_id and item.get("sarees"):
            if saree_id not in product_sales:
                saree_data = item.get("sarees", {})
                product_sales[saree_id] = {
                    "saree_id": saree_id,
                    "name": saree_data.get("name", "Unknown") if isinstance(saree_data, dict) else "Unknown",
                    "fabric_type": saree_data.get("fabric_type", "") if isinstance(saree_data, dict) else "",
                    "quantity_sold": 0,
                    "revenue": 0
                }
            product_sales[saree_id]["quantity_sold"] += item.get("quantity", 0)
            product_sales[saree_id]["revenue"] += item.get("quantity", 0) * float(item.get("unit_price", 0))
    
    top_products = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    
    return DataResponse(
        success=True,
        data={
            "total_revenue": total_revenue,
            "revenue_growth": round(revenue_growth, 1),
            "total_orders": total_orders,
            "orders_growth": round(orders_growth, 1),
            "new_customers": new_customer_count,
            "customers_growth": round(customers_growth, 1),
            "avg_order_value": round(avg_order_value, 2),
            "aov_growth": round(aov_growth, 1),
            "total_customers": total_customers,
            "repeat_customers": repeat_customers,
            "collection_rate": round(collection_rate, 1),
            "outstanding_amount": outstanding_amount,
            "avg_collection_days": 7,  # Placeholder - would need payment timing analysis
            "payment_methods": payment_method_list,
            "top_products": top_products
        }
    )


@router.get("/revenue-over-time", response_model=DataResponse[list])
async def get_revenue_over_time(
    days: int = Query(default=30, ge=7, le=365),
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get revenue data over time for charts.
    
    **Permissions Required:** analytics:read
    """
    from_date = (date.today() - timedelta(days=days)).isoformat()
    
    payments = supabase.table("payments").select("amount, paid_at").gte(
        "paid_at", from_date
    ).order("paid_at").execute()
    
    # Group by day
    daily = {}
    for p in (payments.data or []):
        day_key = p.get("paid_at", "")[:10]  # YYYY-MM-DD format
        if day_key:
            daily[day_key] = daily.get(day_key, 0) + float(p.get("amount", 0))
    
    # Fill in missing days
    revenue_data = []
    current = date.today() - timedelta(days=days)
    while current <= date.today():
        day_str = current.isoformat()
        revenue_data.append({
            "date": day_str,
            "revenue": daily.get(day_str, 0)
        })
        current += timedelta(days=1)
    
    return DataResponse(success=True, data=revenue_data)


@router.get("/inventory", response_model=DataResponse[dict])
async def get_inventory_stats(
    current_user: CurrentUser = Depends(RequirePermission(Permission.ANALYTICS_READ))
):
    """
    Get inventory statistics.
    
    **Permissions Required:** analytics:read
    """
    sarees = supabase.table("sarees").select("*").execute()
    
    total_products = len(sarees.data or [])
    total_stock = sum(s.get("stock_count", 0) for s in (sarees.data or []))
    low_stock_count = sum(1 for s in (sarees.data or []) if 0 < s.get("stock_count", 0) < 5)
    out_of_stock_count = sum(1 for s in (sarees.data or []) if s.get("stock_count", 0) == 0)
    total_value = sum(s.get("selling_price", 0) * s.get("stock_count", 0) for s in (sarees.data or []))
    total_cost = sum((s.get("cost_price", 0) or 0) * s.get("stock_count", 0) for s in (sarees.data or []))
    
    # By category
    by_category = {}
    for s in (sarees.data or []):
        cat = s.get("fabric_type", "Other") or "Other"
        if cat not in by_category:
            by_category[cat] = {"count": 0, "value": 0}
        by_category[cat]["count"] += s.get("stock_count", 0)
        by_category[cat]["value"] += s.get("selling_price", 0) * s.get("stock_count", 0)
    
    category_list = [{"category": k, **v} for k, v in by_category.items()]
    
    return DataResponse(
        success=True,
        data={
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_value": total_value,
            "total_cost": total_cost,
            "by_category": category_list
        }
    )
