"""
API Routers Package
All API endpoint routers for the Saree Business API
"""
from routers import sarees, customers, orders, payments, installments, analytics
from routers.auth import router as auth_router
from routers.invoices import router as invoices_router

__all__ = [
    "sarees",
    "customers", 
    "orders",
    "payments",
    "installments",
    "analytics",
    "auth_router",
    "invoices_router",
]
