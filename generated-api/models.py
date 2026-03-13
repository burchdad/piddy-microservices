"""
User Management API - Models and Schemas

Production-ready Pydantic models for user management system with RBAC.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator


class RoleEnum(str, Enum):
    """User roles for permission-based access control."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    VIEWER = "viewer"


class PermissionEnum(str, Enum):
    """Fine-grained permissions for RBAC."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    is_active: bool = Field(default=True, description="Whether user account is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=255, description="User password (min 8 chars)")
    role: RoleEnum = Field(default=RoleEnum.USER, description="User's initial role")
    
    @validator('password')
    def validate_password(cls, v):
        """Ensure password has mixed complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    role: Optional[RoleEnum] = None


class UserResponse(UserBase):
    """Schema for user response in API."""
    id: str = Field(..., description="User ID (UUID)")
    role: RoleEnum = Field(..., description="User's role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token from previous auth")


class CredentialsRequest(BaseModel):
    """Schema for login credentials."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class PermissionGrant(BaseModel):
    """Schema for granting permissions to users."""
    user_id: str = Field(..., description="User ID")
    permission: PermissionEnum = Field(..., description="Permission to grant")
    resource: str = Field(..., description="Resource the permission applies to")


class RoleAssignment(BaseModel):
    """Schema for assigning roles to users."""
    user_id: str = Field(..., description="User ID")
    role: RoleEnum = Field(..., description="Role to assign")


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
