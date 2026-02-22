"""
Authentication Schemas
Request and response models for authentication endpoints
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Permission enumeration"""
    # Sarees
    SAREES_READ = "sarees:read"
    SAREES_CREATE = "sarees:create"
    SAREES_UPDATE = "sarees:update"
    SAREES_DELETE = "sarees:delete"
    
    # Customers
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_CREATE = "customers:create"
    CUSTOMERS_UPDATE = "customers:update"
    CUSTOMERS_DELETE = "customers:delete"
    
    # Orders
    ORDERS_READ = "orders:read"
    ORDERS_CREATE = "orders:create"
    ORDERS_UPDATE = "orders:update"
    ORDERS_DELETE = "orders:delete"
    
    # Payments
    PAYMENTS_READ = "payments:read"
    PAYMENTS_CREATE = "payments:create"
    PAYMENTS_DELETE = "payments:delete"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    
    # Invoices
    INVOICES_READ = "invoices:read"
    INVOICES_CREATE = "invoices:create"
    
    # Users (Admin only)
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: list(Permission),  # All permissions
    UserRole.MANAGER: [
        Permission.SAREES_READ, Permission.SAREES_CREATE, Permission.SAREES_UPDATE, Permission.SAREES_DELETE,
        Permission.CUSTOMERS_READ, Permission.CUSTOMERS_CREATE, Permission.CUSTOMERS_UPDATE, Permission.CUSTOMERS_DELETE,
        Permission.ORDERS_READ, Permission.ORDERS_CREATE, Permission.ORDERS_UPDATE, Permission.ORDERS_DELETE,
        Permission.PAYMENTS_READ, Permission.PAYMENTS_CREATE, Permission.PAYMENTS_DELETE,
        Permission.ANALYTICS_READ,
        Permission.INVOICES_READ, Permission.INVOICES_CREATE,
    ],
    UserRole.STAFF: [
        Permission.SAREES_READ, Permission.SAREES_CREATE, Permission.SAREES_UPDATE,
        Permission.CUSTOMERS_READ, Permission.CUSTOMERS_CREATE, Permission.CUSTOMERS_UPDATE,
        Permission.ORDERS_READ, Permission.ORDERS_CREATE, Permission.ORDERS_UPDATE,
        Permission.PAYMENTS_READ, Permission.PAYMENTS_CREATE,
        Permission.INVOICES_READ, Permission.INVOICES_CREATE,
    ],
    UserRole.VIEWER: [
        Permission.SAREES_READ,
        Permission.CUSTOMERS_READ,
        Permission.ORDERS_READ,
        Permission.PAYMENTS_READ,
        Permission.ANALYTICS_READ,
        Permission.INVOICES_READ,
    ],
}


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    role: UserRole = UserRole.STAFF
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class LoginUserResponse(BaseModel):
    """User info returned on login"""
    id: str
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: LoginUserResponse


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


class UserResponse(BaseModel):
    """User response (public data)"""
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")


class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
