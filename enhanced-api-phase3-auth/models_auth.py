"""
Authentication Service - SQLAlchemy ORM Models
OAuth providers, sessions, MFA tokens, audit logs
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Enum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database_auth import Base
import uuid
from datetime import datetime
from enum import Enum as PyEnum


class OAuthProvider(PyEnum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    OKTA = "okta"


class MFAMethod(PyEnum):
    """Supported MFA methods"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"


class OAuthAccount(Base):
    """OAuth provider account linking"""
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        Index("idx_user_provider", "user_id", "provider"),
        Index("idx_provider_id", "provider", "provider_user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # google, github, microsoft, okta
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=False)
    provider_data = Column(JSONB, nullable=True)  # Store provider-specific metadata
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_primary = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")


class SAMLConfiguration(Base):
    """SAML provider configuration"""
    __tablename__ = "saml_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    organization_id = Column(String(255), nullable=True)
    idp_entity_id = Column(String(512), nullable=False)
    sso_url = Column(String(512), nullable=False)
    certificate = Column(Text, nullable=False)
    metadata_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=False)


class SAMLAssertion(Base):
    """SAML sign-on assertion records"""
    __tablename__ = "saml_assertions"
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    saml_config_id = Column(UUID(as_uuid=True), ForeignKey("saml_configurations.id"), nullable=False)
    assertion_id = Column(String(255), nullable=False, unique=True)
    assertion_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SessionToken(Base):
    """Auth session tokens (extends Phase 1)"""
    __tablename__ = "session_tokens"
    __table_args__ = (
        Index("idx_user_token", "user_id", "token"),
        Index("idx_expires", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    token_type = Column(String(50), default="bearer")  # bearer, refresh, etc
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    user_agent = Column(String(512), nullable=False)
    device_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


class MFADevice(Base):
    """Multi-factor authentication devices"""
    __tablename__ = "mfa_devices"
    __table_args__ = (
        Index("idx_user_method", "user_id", "method"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    method = Column(String(50), nullable=False)  # totp, sms, email
    name = Column(String(255), nullable=False)  # e.g. "iPhone Authenticator", "Phone +1-555-0123"
    secret = Column(String(255), nullable=False)  # Encrypted TOTP secret or verified contact
    is_primary = Column(Boolean, default=False)
    is_backup = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    verified_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    backup_codes = Column(JSONB, nullable=True)  # Encrypted backup codes

    # Relationships
    user = relationship("User", back_populates="mfa_devices")


class MFAChallenge(Base):
    """Active MFA challenges"""
    __tablename__ = "mfa_challenges"
    __table_args__ = (
        Index("idx_user_expires", "user_id", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("mfa_devices.id"), nullable=False)
    challenge_code = Column(String(255), nullable=False)  # Random challenge
    method = Column(String(50), nullable=False)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)


class AuthAuditLog(Base):
    """Authentication audit trail"""
    __tablename__ = "auth_audit_logs"
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "created_at"),
        Index("idx_action", "action", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # login, logout, mfa_verified, oauth_connected
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(512), nullable=False)
    provider = Column(String(50), nullable=True)  # For OAuth/SAML
    status = Column(String(20), nullable=False)  # success, failure, suspicious
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    """User model (synchronized with Phase 1 User table)"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
    sessions = relationship("SessionToken", back_populates="user")
    mfa_devices = relationship("MFADevice", back_populates="user")
