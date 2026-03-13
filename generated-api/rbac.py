"""
Role-Based Access Control (RBAC) Middleware

Implements fine-grained permission checking for API endpoints.
"""

from typing import Callable, Optional
from functools import wraps
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from auth import auth_service, verify_permissions


security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    """
    Extract and validate JWT token from request.
    This is a FastAPI dependency that can be used in route handlers.
    """
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify user has admin role.
    Dependency for admin-only endpoints.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin access required."
        )
    return current_user


async def require_permission(permission: str):
    """
    Factory function to create permission-based dependency.
    
    Usage:
        @app.get("/resource")
        async def get_resource(current_user = Depends(require_permission("read"))):
            ...
    """
    async def check_permission(current_user: dict = Depends(get_current_user)) -> dict:
        if not verify_permissions(current_user.get("role", ""), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required for this operation"
            )
        return current_user
    
    return check_permission


class RBACMiddleware:
    """
    Middleware for request-level permission checking.
    Can be used to enforce permissions at the application level.
    """
    
    def __init__(self, required_permission: Optional[str] = None):
        self.required_permission = required_permission
    
    async def __call__(self, request, call_next):
        """Process request and enforce permissions."""
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            # Allow public endpoints
            return await call_next(request)
        
        try:
            token = auth_header.replace("Bearer ", "")
            payload = auth_service.verify_token(token)
            
            # Check permission if specified
            if self.required_permission:
                if not verify_permissions(payload.get("role"), self.required_permission):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": "Insufficient permissions"}
                    )
            
            # Attach user info to request state
            request.state.user = payload
            
        except ValueError:
            # Invalid token, but don't fail - let endpoint handle it
            pass
        
        return await call_next(request)


def require_role(*roles: str) -> Callable:
    """
    Decorator for requiring specific roles.
    
    Usage:
        @require_role("admin", "moderator")
        async def admin_endpoint(current_user = Depends(get_current_user)):
            ...
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires one of these roles: {', '.join(roles)}"
            )
        return current_user
    
    return Depends(role_checker)


def audit_log(action: str):
    """
    Decorator to log access for audit trail.
    
    Usage:
        @audit_log("user_deletion")
        async def delete_user(user_id: str, current_user = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # In production, log to audit database
            print(f"[AUDIT] {action} by {kwargs.get('current_user', {}).get('email', 'unknown')}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
