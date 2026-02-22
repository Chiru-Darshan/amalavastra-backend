"""
Authentication Service
Business logic for user authentication and management
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from database import supabase, supabase_admin
from core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token
)
from core.config import settings
from core.exceptions import (
    AuthenticationError, ValidationError, ConflictError, ResourceNotFoundError
)
from core.logging import logger, log_security_event
from schemas.auth import UserRole, ROLE_PERMISSIONS


class AuthService:
    """Service for authentication and user management"""
    
    @staticmethod
    async def register_user(
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.STAFF
    ) -> Dict[str, Any]:
        """Register a new user"""
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Check if email already exists (use admin client for registration)
        existing = supabase_admin.table("users").select("id").eq("email", email.lower()).execute()
        if existing.data:
            raise ConflictError("Email already registered")
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user record
        user_data = {
            "email": email.lower(),
            "password_hash": hashed_password,
            "full_name": full_name,
            "phone": phone,
            "role": role.value,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase_admin.table("users").insert(user_data).execute()
        
        if not result.data:
            raise ValidationError("Failed to create user")
        
        user = result.data[0]
        
        log_security_event("USER_REGISTERED", {
            "user_id": user["id"],
            "email": email,
            "role": role.value
        })
        
        # Remove sensitive data before returning
        user.pop("password_hash", None)
        
        return user
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        
        # Fetch user (use admin client to bypass RLS for authentication)
        result = supabase_admin.table("users").select("*").eq("email", email.lower()).execute()
        
        print(f"DEBUG - Login attempt for: {email.lower()}")
        print(f"DEBUG - User found: {bool(result.data)}")
        
        if not result.data:
            log_security_event("LOGIN_FAILED", {
                "email": email,
                "reason": "User not found"
            }, severity="WARNING")
            raise AuthenticationError("Invalid email or password")
        
        user = result.data[0]
        print(f"DEBUG - User active: {user.get('is_active')}")
        print(f"DEBUG - Password hash exists: {bool(user.get('password_hash'))}")
        print(f"DEBUG - Password hash: {user.get('password_hash')[:50]}...")
        
        # Check if user is active
        if not user.get("is_active", True):
            log_security_event("LOGIN_FAILED", {
                "email": email,
                "reason": "Account deactivated"
            }, severity="WARNING")
            raise AuthenticationError("Account is deactivated")
        
        # Verify password
        password_valid = verify_password(password, user.get("password_hash", ""))
        print(f"DEBUG - Password verification result: {password_valid}")
        
        if not password_valid:
            log_security_event("LOGIN_FAILED", {
                "email": email,
                "reason": "Invalid password"
            }, severity="WARNING")
            raise AuthenticationError("Invalid email or password")
        
        # Update last login (use admin client)
        supabase_admin.table("users").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("id", user["id"]).execute()
        
        # Create tokens
        token_data = {
            "sub": user["id"],
            "email": user["email"],
            "role": user.get("role", "viewer"),
            "is_active": user.get("is_active", True)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        log_security_event("LOGIN_SUCCESS", {
            "user_id": user["id"],
            "email": email
        })
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user.get("full_name"),
                "role": user.get("role")
            }
        }
    
    @staticmethod
    async def refresh_tokens(refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        
        payload = decode_token(refresh_token)
        
        if not payload:
            raise AuthenticationError("Invalid refresh token")
        
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        # Fetch user to ensure still active
        user_id = payload.get("sub")
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not result.data:
            raise AuthenticationError("User not found")
        
        user = result.data[0]
        
        if not user.get("is_active", True):
            raise AuthenticationError("Account is deactivated")
        
        # Create new tokens
        token_data = {
            "sub": user["id"],
            "email": user["email"],
            "role": user.get("role", "viewer"),
            "is_active": user.get("is_active", True)
        }
        
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    async def change_password(
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password"""
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Fetch user
        result = supabase.table("users").select("password_hash").eq("id", user_id).execute()
        
        if not result.data:
            raise ResourceNotFoundError("User", user_id)
        
        # Verify current password
        if not verify_password(current_password, result.data[0].get("password_hash", "")):
            raise AuthenticationError("Current password is incorrect")
        
        # Update password
        new_hash = hash_password(new_password)
        supabase.table("users").update({
            "password_hash": new_hash,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        log_security_event("PASSWORD_CHANGED", {
            "user_id": user_id
        })
        
        return True
    
    @staticmethod
    async def get_user(user_id: str) -> Dict[str, Any]:
        """Get user by ID"""
        result = supabase.table("users").select(
            "id, email, full_name, phone, role, is_active, created_at, last_login"
        ).eq("id", user_id).execute()
        
        if not result.data:
            raise ResourceNotFoundError("User", user_id)
        
        return result.data[0]
    
    @staticmethod
    async def list_users(
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List users with pagination"""
        
        query = supabase_admin.table("users").select(
            "id, email, full_name, phone, role, is_active, created_at, last_login",
            count="exact"
        )
        
        if role:
            query = query.eq("role", role.value)
        if is_active is not None:
            query = query.eq("is_active", is_active)
        
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
    async def update_user(
        user_id: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update user details"""
        
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if full_name is not None:
            update_data["full_name"] = full_name
        if phone is not None:
            update_data["phone"] = phone
        if role is not None:
            update_data["role"] = role.value
        if is_active is not None:
            update_data["is_active"] = is_active
        
        result = supabase.table("users").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            raise ResourceNotFoundError("User", user_id)
        
        user = result.data[0]
        user.pop("password_hash", None)
        
        return user
    
    @staticmethod
    async def deactivate_user(user_id: str) -> bool:
        """Deactivate a user account"""
        result = supabase.table("users").update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not result.data:
            raise ResourceNotFoundError("User", user_id)
        
        log_security_event("USER_DEACTIVATED", {
            "user_id": user_id
        })
        
        return True
