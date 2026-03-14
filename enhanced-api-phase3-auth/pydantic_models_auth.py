"""
Authentication Service - Pydantic Models
Request/response schemas for API endpoints
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import uuid


# OAuth & Provider Schemas
class OAuthProviderRequest(BaseModel):
    """Request to initiate OAuth flow"""
    provider: str = Field(..., description="OAuth provider: google, github, microsoft, okta")
    redirect_uri: str = Field(..., description="Redirect URI after OAuth callback")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback with auth code"""
    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State parameter for CSRF protection")
    provider: str = Field(..., description="OAuth provider identifier")


class OAuthAccountResponse(BaseModel):
    """OAuth account information"""
    id: uuid.UUID
    provider: str
    provider_email: str
    is_primary: bool
    connected_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class LinkedAccountsResponse(BaseModel):
    """List of linked OAuth accounts"""
    oauth_accounts: List[OAuthAccountResponse]
    primary_account: OAuthAccountResponse


# SAML Schemas
class SAMLConfigurationRequest(BaseModel):
    """Create/update SAML configuration"""
    name: str = Field(..., description="SAML configuration name")
    idp_entity_id: str = Field(..., description="Identity Provider Entity ID")
    sso_url: str = Field(..., description="Single Sign-On URL")
    certificate: str = Field(..., description="IdP certificate (PEM format)")
    metadata_url: Optional[str] = Field(None, description="Metadata URL (optional)")


class SAMLConfigurationResponse(BaseModel):
    """SAML configuration response"""
    id: uuid.UUID
    name: str
    idp_entity_id: str
    sso_url: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SAMLInitiateRequest(BaseModel):
    """Initiate SAML login"""
    saml_config_id: uuid.UUID
    relay_state: Optional[str] = Field(None, description="RelayState parameter")


class SAMLInitiateResponse(BaseModel):
    """SAML login response"""
    sso_url: str
    request_id: str
    relay_state: Optional[str]


# MFA Schemas
class MFASetupRequest(BaseModel):
    """Setup new MFA device"""
    method: str = Field(..., description="totp, sms, or email")
    name: str = Field(..., description="Device name (e.g., 'iPhone Authenticator')")
    phone_number: Optional[str] = Field(None, description="Phone for SMS/EMAIL methods")


class MFASetupResponse(BaseModel):
    """MFA setup response with secret"""
    device_id: uuid.UUID
    method: str
    name: str
    secret: Optional[str] = Field(None, description="TOTP secret (share as QR code)")
    qr_code_url: Optional[str] = Field(None, description="QR code image URL")


class MFAVerifyRequest(BaseModel):
    """Verify MFA code"""
    device_id: uuid.UUID
    code: str = Field(..., description="6-digit TOTP code or SMS/Email code")


class MFADeviceResponse(BaseModel):
    """MFA device information"""
    id: uuid.UUID
    method: str
    name: str
    is_primary: bool
    is_backup: bool
    is_active: bool
    verified_at: Optional[datetime]
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class MFAChallengeRequest(BaseModel):
    """Request MFA challenge"""
    user_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None


class MFAChallengeResponse(BaseModel):
    """MFA challenge response"""
    challenge_id: uuid.UUID
    method: str
    message: str = "Code sent to your device"


class MFAVerifyResponse(BaseModel):
    """MFA verification success"""
    success: bool
    token: str = Field(..., description="Session token after MFA verification")


class BackupCodesResponse(BaseModel):
    """MFA backup codes"""
    backup_codes: List[str]
    device_id: uuid.UUID


# Session Token Schemas
class SessionTokenResponse(BaseModel):
    """Active session information"""
    id: uuid.UUID
    device_name: Optional[str]
    ip_address: str
    user_agent: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: datetime

    class Config:
        from_attributes = True


class ListSessionsResponse(BaseModel):
    """List of user sessions"""
    sessions: List[SessionTokenResponse]
    total: int


class RevokeSessionRequest(BaseModel):
    """Revoke a session"""
    session_id: uuid.UUID
    reason: Optional[str] = None


# Authentication Flow Schemas
class LoginRequest(BaseModel):
    """Regular login credentials"""
    email: EmailStr
    password: str
    device_name: Optional[str] = Field(None, description="Device identifier")


class LoginResponse(BaseModel):
    """Login response"""
    token: str
    refresh_token: str
    user_id: uuid.UUID
    mfa_required: bool = False
    mfa_challenge_id: Optional[uuid.UUID] = None


class RefreshTokenRequest(BaseModel):
    """Refresh access token"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Logout request"""
    all_devices: bool = Field(False, description="Logout all sessions if True")


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool
    message: str


# User Profile Schemas
class UserProfileResponse(BaseModel):
    """User profile with auth status"""
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    oauth_accounts: List[OAuthAccountResponse]
    mfa_devices: List[MFADeviceResponse]

    class Config:
        from_attributes = True


# Auth Audit Log Schemas
class AuthAuditLogResponse(BaseModel):
    """Authentication audit log entry"""
    id: uuid.UUID
    action: str
    ip_address: str
    status: str
    provider: Optional[str]
    created_at: datetime
    details: Optional[dict]

    class Config:
        from_attributes = True


class ListAuditLogsResponse(BaseModel):
    """List of audit logs"""
    logs: List[AuthAuditLogResponse]
    total: int
    page: int
    size: int


# Error Response Schemas
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error details"""
    error: str = "validation_error"
    details: List[dict]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Health Check Schemas
class HealthCheckResponse(BaseModel):
    """Service health status"""
    status: str  # healthy, degraded, unhealthy
    version: str
    database: str  # connected, disconnected
    redis: str  # connected, disconnected, optional
    timestamp: datetime
    uptime_seconds: int
