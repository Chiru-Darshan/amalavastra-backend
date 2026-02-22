"""
Saree Business API - Professional Grade
A secure, scalable REST API for saree business management

Features:
- JWT Authentication with Role-Based Access Control
- Rate Limiting & Security Headers
- Invoice Generation with PDF Export
- Comprehensive Logging & Error Handling
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import time

from core.config import settings
from core.logging import logger
from core.exceptions import BaseAPIException
from middleware.security import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware
)
from routers import sarees, customers, orders, payments, installments, analytics
from routers.auth import router as auth_router
from routers.invoices import router as invoices_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Saree Business Management API

A professional-grade REST API for managing saree inventory, orders, customers, and payments.

### Features
- 🔐 **JWT Authentication** - Secure token-based authentication
- 👥 **Role-Based Access Control** - Admin, Manager, Staff, Viewer roles
- 📊 **Business Analytics** - Revenue reports, sales trends, inventory insights
- 🧾 **Invoice Generation** - Professional PDF invoices with GST
- 💳 **Payment Tracking** - Full and installment payment support
- 📦 **Inventory Management** - Stock tracking with low-stock alerts

### Authentication
All endpoints (except `/api/auth/login`) require a valid JWT token.
Include the token in the `Authorization` header as `Bearer <token>`.
    """,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token"
        }
    }
    
    # Apply security globally
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting (only in production)
if settings.ENVIRONMENT == "production":
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


# CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Global exception handler
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "detail": exc.detail,
            "path": str(request.url.path)
        },
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "detail": "An unexpected error occurred" if not settings.DEBUG else str(exc),
            "path": str(request.url.path)
        }
    )


# Include routers with proper prefixes and tags
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    sarees.router,
    prefix="/api/sarees",
    tags=["Sarees"]
)

app.include_router(
    customers.router,
    prefix="/api/customers",
    tags=["Customers"]
)

app.include_router(
    orders.router,
    prefix="/api/orders",
    tags=["Orders"]
)

app.include_router(
    payments.router,
    prefix="/api/payments",
    tags=["Payments"]
)

app.include_router(
    installments.router,
    prefix="/api/installments",
    tags=["Installments"]
)

app.include_router(
    invoices_router,
    prefix="/api/invoices",
    tags=["Invoices"]
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["Analytics"]
)


# Health check endpoint (no auth required)
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/api/health", tags=["Health"])
async def api_health():
    """API health check with database connectivity test"""
    from database import supabase
    
    try:
        # Test database connection
        supabase.table("sarees").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "api_status": "healthy",
        "database_status": db_status,
        "version": settings.APP_VERSION
    }

