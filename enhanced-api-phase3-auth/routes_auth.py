"""
Authentication Service - FastAPI Routes
REST API endpoints for auth, OAuth, SAML, MFA
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import os
import uuid

from database_auth import get_db, init_db
from models_auth import User, SessionToken, AuthAuditLog, MFADevice
from pydantic_models_auth import (
    OAuthProviderRequest,
    OAuthCallbackRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    LogoutRequest,
    LogoutResponse,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    UserProfileResponse,
    SessionTokenResponse,
    ListSessionsResponse,
    HealthCheckResponse,
    ErrorResponse,
)
from oauth_service import OAuthService
from mfa_service import MFAService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Piddy Authentication Service",
    description="OAuth2, SAML, and MFA authentication service",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Initialize services
oauth_service = OAuthService()
mfa_service = MFAService()

# App startup
@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Authentication Service started")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Authentication Service stopped")


# ============================================================================
# Health & Monitoring
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Check service health"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
        raise HTTPException(status_code=503, detail="Database unavailable")

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        database=db_status,
        redis="optional",
        timestamp=datetime.utcnow(),
        uptime_seconds=0,
    )


@app.get("/metrics", tags=["Health"])
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    users = db.query(User).count()
    oauth_accounts = db.query(User).filter(User.oauth_accounts.any()).count()
    mfa_enabled = db.query(User).filter(User.mfa_enabled).count()

    return {
        "total_users": users,
        "oauth_users": oauth_accounts,
        "mfa_enabled_users": mfa_enabled,
        "timestamp": datetime.utcnow(),
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.post("/oauth/authorize", tags=["OAuth"])
def get_oauth_url(
    request: OAuthProviderRequest,
    db: Session = Depends(get_db),
):
    """Get OAuth authorization URL"""
    try:
        auth_data = oauth_service.get_authorization_url(
            request.provider,
            request.redirect_uri,
        )
        return auth_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/oauth/callback", response_model=LoginResponse, tags=["OAuth"])
async def handle_oauth_callback(
    request: OAuthCallbackRequest,
    redirect_uri: str,
    db: Session = Depends(get_db),
):
    """Handle OAuth provider callback"""
    try:
        user, oauth_account = await oauth_service.handle_callback(
            request,
            redirect_uri,
            db,
        )

        # Create session token
        token = _create_session_token(user.id, db, "oauth_login")

        # Log audit trail
        _log_audit(
            db,
            user.id,
            "oauth_login",
            request,
            "success",
            {"provider": request.provider},
        )

        return LoginResponse(
            token=token.token,
            refresh_token=token.token,
            user_id=user.id,
            mfa_required=False,
        )
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")


@app.get("/oauth/accounts", response_model=list, tags=["OAuth"])
def list_oauth_accounts(
    user_id: str,
    db: Session = Depends(get_db),
):
    """List linked OAuth accounts"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return [
        {
            "id": str(acc.id),
            "provider": acc.provider,
            "email": acc.provider_email,
            "connected_at": acc.connected_at,
        }
        for acc in user.oauth_accounts
    ]


# ============================================================================
# MFA Endpoints
# ============================================================================

@app.post("/mfa/setup", response_model=MFASetupResponse, tags=["MFA"])
def setup_mfa(
    request: MFASetupRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Setup MFA device"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        if request.method == "totp":
            device, secret, qr_code = mfa_service.setup_totp(
                user_id,
                request.name,
                db,
            )
            return MFASetupResponse(
                device_id=device.id,
                method="totp",
                name=request.name,
                secret=secret,
                qr_code_url=qr_code,
            )
        elif request.method == "sms":
            device = mfa_service.setup_sms(
                user_id,
                request.phone_number,
                request.name,
                db,
            )
            return MFASetupResponse(
                device_id=device.id,
                method="sms",
                name=request.name,
            )
        elif request.method == "email":
            device = mfa_service.setup_email(
                user_id,
                user.email,
                request.name,
                db,
            )
            return MFASetupResponse(
                device_id=device.id,
                method="email",
                name=request.name,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mfa/verify-setup", tags=["MFA"])
def verify_mfa_setup(
    device_id: str,
    code: str,
    db: Session = Depends(get_db),
):
    """Verify MFA device setup"""
    try:
        device, backup_codes = mfa_service.verify_setup(device_id, code, db)
        return {
            "success": True,
            "device_id": str(device.id),
            "backup_codes": backup_codes,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mfa/challenge", tags=["MFA"])
def request_mfa_challenge(
    user_id: str,
    device_id: str = None,
    db: Session = Depends(get_db),
):
    """Request MFA challenge"""
    try:
        challenge = mfa_service.create_challenge(user_id, device_id, db)
        return {
            "challenge_id": str(challenge.id),
            "method": challenge.method,
            "expires_in": 600,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mfa/verify-challenge", tags=["MFA"])
def verify_mfa_challenge(
    challenge_id: str,
    code: str,
    db: Session = Depends(get_db),
):
    """Verify MFA challenge response"""
    try:
        verified, device = mfa_service.verify_challenge(challenge_id, code, db)
        return {
            "success": verified,
            "device_id": str(device.id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mfa/devices", tags=["MFA"])
def list_mfa_devices(
    user_id: str,
    db: Session = Depends(get_db),
):
    """List user's MFA devices"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    devices = mfa_service.list_devices(user_id, db)
    return {
        "devices": [
            {
                "id": str(d.id),
                "method": d.method,
                "name": d.name,
                "is_primary": d.is_primary,
                "verified_at": d.verified_at,
            }
            for d in devices
        ]
    }


# ============================================================================
# Session Management
# ============================================================================

@app.get("/sessions", response_model=ListSessionsResponse, tags=["Sessions"])
def list_sessions(
    user_id: str,
    db: Session = Depends(get_db),
):
    """List user's active sessions"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = (
        db.query(SessionToken)
        .filter(
            SessionToken.user_id == user_id,
            SessionToken.is_active,
        )
        .all()
    )

    return ListSessionsResponse(
        sessions=[
            SessionTokenResponse(
                id=s.id,
                device_name=s.device_name,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_active=s.is_active,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@app.post("/sessions/revoke", tags=["Sessions"])
def revoke_session(
    user_id: str,
    session_id: str,
    db: Session = Depends(get_db),
):
    """Revoke specific session"""
    session = db.query(SessionToken).filter(SessionToken.id == session_id).first()
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    session.revoked_at = datetime.utcnow()
    db.commit()

    return {"success": True}


# ============================================================================
# User Profile
# ============================================================================

@app.get("/users/{user_id}", response_model=UserProfileResponse, tags=["Users"])
def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get user profile with auth status"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_verified=user.is_verified,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        oauth_accounts=user.oauth_accounts,
        mfa_devices=user.mfa_devices,
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _create_session_token(user_id: str, db: Session, action: str) -> SessionToken:
    """Create session token"""
    token = SessionToken(
        user_id=user_id,
        token=f"auth_{uuid.uuid4().hex}",
        token_type="bearer",
        ip_address="0.0.0.0",  # From request context in real app
        user_agent="piddy-client",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(token)
    db.commit()
    return token


def _log_audit(
    db: Session,
    user_id: str,
    action: str,
    request: Request,
    status: str,
    details: dict = None,
):
    """Log authentication audit event"""
    log = AuthAuditLog(
        user_id=user_id,
        action=action,
        ip_address="0.0.0.0",
        user_agent="piddy-client",
        status=status,
        details=details,
    )
    db.add(log)
    db.commit()


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
