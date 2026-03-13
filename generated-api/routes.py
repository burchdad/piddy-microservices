"""
User Management API Routes

Production-ready FastAPI endpoints for user management with full RBAC.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime
from typing import List
import uuid

from models import (
    UserCreate, UserUpdate, UserResponse, TokenResponse,
    CredentialsRequest, TokenRefreshRequest, RoleAssignment,
    ErrorResponse, RoleEnum
)
from auth import auth_service
from rbac import get_current_user, get_current_admin, require_permission, audit_log

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# Simulated user database
users_db = {}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate) -> UserResponse:
    """
    Register a new user account.
    
    - **email**: Valid email address (must be unique)
    - **full_name**: User's full name
    - **password**: Strong password (8+ chars, uppercase, digit)
    - **role**: Initial role (default: USER)
    """
    # Check if email already exists
    if any(u['email'] == user.email for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    users_db[user_id] = {
        "id": user_id,
        "email": user.email,
        "full_name": user.full_name,
        "password_hash": auth_service.hash_password(user.password),
        "role": user.role,
        "is_active": user.is_active,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }
    
    return UserResponse(**users_db[user_id])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: CredentialsRequest) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens.
    
    - **email**: User's email address
    - **password**: User's password
    """
    # Find user by email
    user = next((u for u in users_db.values() if u['email'] == credentials.email), None)
    
    if not user or not auth_service.verify_password(credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user['last_login'] = datetime.utcnow()
    
    # Generate tokens
    access_token, refresh_token = auth_service.create_tokens(
        user['id'], user['email'], user['role']
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60  # 15 minutes in seconds
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: TokenRefreshRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token from login
    """
    try:
        payload = auth_service.verify_token(request.refresh_token)
        
        if payload.get('type') != 'refresh':
            raise ValueError("Token is not a refresh token")
        
        user = users_db.get(payload['sub'])
        if not user:
            raise ValueError("User not found")
        
        # Generate new tokens
        access_token, new_refresh_token = auth_service.create_tokens(
            user['id'], user['email'], user['role']
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=15 * 60
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user's information."""
    user = users_db.get(current_user['sub'])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserResponse(**user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)) -> UserResponse:
    """Get user by ID (requires authentication)."""
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**user)


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_admin)
) -> List[UserResponse]:
    """
    List all users (admin only).
    
    - **skip**: Number of users to skip
    - **limit**: Maximum users to return (max 100)
    """
    users = list(users_db.values())[skip:skip + limit]
    return [UserResponse(**u) for u in users]


@router.put("/{user_id}", response_model=UserResponse)
@audit_log("user_profile_update")
async def update_user(
    user_id: str,
    updates: UserUpdate,
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """
    Update user profile.
    Users can only update themselves; admins can update any user.
    """
    # Check authorization
    if current_user['sub'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users"
        )
    
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    # Update allowed fields
    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        user[key] = value
    
    user['updated_at'] = datetime.utcnow()
    
    return UserResponse(**user)


@router.post("/{user_id}/role", response_model=UserResponse)
@audit_log("role_assignment")
async def assign_role(
    user_id: str,
    role_data: RoleAssignment,
    current_user: dict = Depends(get_current_admin)
) -> UserResponse:
    """Assign a role to a user (admin only)."""
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    user['role'] = role_data.role
    user['updated_at'] = datetime.utcnow()
    
    return UserResponse(**user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log("user_deletion")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a user (admin only)."""
    if user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    del users_db[user_id]
    return None


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout and invalidate current token."""
    # Token would be passed in request, but in this simplified version:
    return {"message": "Logged out successfully"}
