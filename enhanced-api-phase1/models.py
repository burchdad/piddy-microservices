"""
SQLAlchemy ORM Models for User Management

Production-ready database models with proper relationships and constraints.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from database import Base


class RoleEnum(PyEnum):
    """User roles."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    VIEWER = "viewer"


class User(Base):
    """User model for database persistence."""
    __tablename__ = "users"
    
    __table_args__ = (
        UniqueConstraint('email', name='uq_user_email'),
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
        Index('idx_user_created', 'created_at'),
        Index('idx_user_active', 'is_active'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    role = Column(String(50), default=RoleEnum.USER.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class UserSession(Base):
    """Track user sessions for token management."""
    __tablename__ = "user_sessions"
    
    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_token', 'token_hash'),
        Index('idx_session_expires', 'expires_at'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    
    token_hash = Column(String(255), nullable=False, unique=True)
    refresh_token_hash = Column(String(255), nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """Audit trail for compliance and security."""
    __tablename__ = "audit_logs"
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    resource_id = Column(String(255), nullable=True)
    
    details = Column(String(1000), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(50), nullable=False, default="success")
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
