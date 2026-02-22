"""
Authentication Dependencies
FastAPI dependencies for authentication and authorization
"""
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List

from core.security import decode_token
from core.exceptions import AuthenticationError, AuthorizationError
from core.logging import log_security_event
from schemas.auth import UserRole, Permission, ROLE_PERMISSIONS


# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the current authenticated user"""
    
    def __init__(
        self,
        id: str,
        email: str,
        role: UserRole,
        permissions: List[Permission],
        is_active: bool = True
    ):
        self.id = id
        self.email = email
        self.role = role
        self.permissions = permissions
        self.is_active = is_active
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions"""
        return all(p in self.permissions for p in permissions)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    Get the current authenticated user from JWT token.
    Raises AuthenticationError if token is invalid or missing.
    """
    if not credentials:
        raise AuthenticationError("Missing authentication token")
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        log_security_event(
            "INVALID_TOKEN",
            {"ip": request.client.host if request.client else "unknown"},
            severity="WARNING"
        )
        raise AuthenticationError("Invalid or expired token")
    
    # Check token type
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    
    # Extract user data
    user_id = payload.get("sub")
    email = payload.get("email")
    role_str = payload.get("role", "viewer")
    is_active = payload.get("is_active", True)
    
    if not user_id or not email:
        raise AuthenticationError("Invalid token payload")
    
    if not is_active:
        raise AuthenticationError("User account is deactivated")
    
    # Get role and permissions
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.VIEWER
    
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    # Store user ID in request state for logging
    request.state.user_id = user_id
    
    return CurrentUser(
        id=user_id,
        email=email,
        role=role,
        permissions=permissions,
        is_active=is_active
    )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """
    Get the current user if authenticated, otherwise return None.
    Does not raise an error if no token is provided.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(request, credentials)
    except AuthenticationError:
        return None


class RequirePermission:
    """Dependency class to require specific permissions"""
    
    def __init__(self, *permissions: Permission):
        self.permissions = list(permissions)
    
    async def __call__(
        self,
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if not current_user.has_any_permission(self.permissions):
            log_security_event(
                "PERMISSION_DENIED",
                {
                    "user_id": current_user.id,
                    "required_permissions": [p.value for p in self.permissions],
                    "user_role": current_user.role.value
                },
                severity="WARNING"
            )
            raise AuthorizationError(
                f"Required permissions: {', '.join(p.value for p in self.permissions)}"
            )
        return current_user


class RequireRole:
    """Dependency class to require specific roles"""
    
    def __init__(self, *roles: UserRole):
        self.roles = list(roles)
    
    async def __call__(
        self,
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if current_user.role not in self.roles:
            log_security_event(
                "ROLE_DENIED",
                {
                    "user_id": current_user.id,
                    "required_roles": [r.value for r in self.roles],
                    "user_role": current_user.role.value
                },
                severity="WARNING"
            )
            raise AuthorizationError(
                f"Required roles: {', '.join(r.value for r in self.roles)}"
            )
        return current_user


# Convenience dependency instances
require_admin = RequireRole(UserRole.ADMIN)
require_manager = RequireRole(UserRole.ADMIN, UserRole.MANAGER)
require_staff = RequireRole(UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF)
