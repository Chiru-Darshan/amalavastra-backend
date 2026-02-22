"""
Authentication Router
Handles user registration, login, and token management
"""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from typing import Optional

from schemas.auth import (
    UserRegister, UserLogin, TokenResponse, TokenRefresh,
    UserResponse, UserUpdate, PasswordChange, UserRole
)
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from services.auth_service import AuthService
from dependencies.auth import (
    get_current_user, CurrentUser, RequireRole, require_admin
)
from core.logging import log_security_event


router = APIRouter()


@router.post("/register", response_model=DataResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    current_user: CurrentUser = Depends(require_admin)  # Only admins can register new users
):
    """
    Register a new user.
    
    **Requires Admin role.**
    
    - **email**: Valid email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **full_name**: User's full name
    - **phone**: Optional phone number
    - **role**: User role (admin, manager, staff, viewer)
    """
    user = await AuthService.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role
    )
    
    return DataResponse(
        success=True,
        message="User registered successfully",
        data=user
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """
    Authenticate user and get access tokens.
    
    Returns:
    - **access_token**: JWT for API access (expires in 30 minutes)
    - **refresh_token**: JWT for token refresh (expires in 7 days)
    """
    result = await AuthService.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )
    
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """
    Refresh access token using refresh token.
    
    Use this endpoint to get a new access token when the current one expires.
    """
    result = await AuthService.refresh_tokens(token_data.refresh_token)
    return result


@router.get("/me", response_model=DataResponse[UserResponse])
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    """
    user = await AuthService.get_user(current_user.id)
    
    return DataResponse(
        success=True,
        data=user
    )


@router.put("/me", response_model=DataResponse[UserResponse])
async def update_current_user(
    user_data: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update current user's profile.
    
    Users can only update their own name and phone.
    """
    user = await AuthService.update_user(
        user_id=current_user.id,
        full_name=user_data.full_name,
        phone=user_data.phone
    )
    
    return DataResponse(
        success=True,
        message="Profile updated successfully",
        data=user
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Change current user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New strong password
    """
    await AuthService.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )
    
    return MessageResponse(
        success=True,
        message="Password changed successfully"
    )


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    List all users with pagination.
    
    **Requires Admin role.**
    """
    result = await AuthService.list_users(
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active
    )
    
    return PaginatedResponse(
        success=True,
        **result
    )


@router.get("/users/{user_id}", response_model=DataResponse[UserResponse])
async def get_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Get user by ID.
    
    **Requires Admin role.**
    """
    user = await AuthService.get_user(user_id)
    
    return DataResponse(
        success=True,
        data=user
    )


@router.put("/users/{user_id}", response_model=DataResponse[UserResponse])
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Update user by ID.
    
    **Requires Admin role.**
    """
    user = await AuthService.update_user(
        user_id=user_id,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=role,
        is_active=is_active
    )
    
    return DataResponse(
        success=True,
        message="User updated successfully",
        data=user
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Deactivate a user account.
    
    **Requires Admin role.**
    
    Note: This does not delete the user, only deactivates the account.
    """
    if user_id == current_user.id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Cannot deactivate your own account"}
        )
    
    await AuthService.deactivate_user(user_id)
    
    return MessageResponse(
        success=True,
        message="User deactivated successfully"
    )
