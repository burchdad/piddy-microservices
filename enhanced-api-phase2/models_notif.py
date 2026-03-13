"""
Phase 2 Database Models - Notification Service

Multi-tenant notification system with delivery tracking.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from database_notif import Base


class NotificationType(PyEnum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationStatus(PyEnum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class Notification(Base):
    """Notification model."""
    __tablename__ = "notifications"
    
    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_type', 'notification_type'),
        Index('idx_notification_created', 'created_at'),
        Index('idx_notification_read', 'is_read'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    
    notification_type = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    is_read = Column(Boolean, default=False, nullable=False)
    delivery_status = Column(String(50), default=NotificationStatus.PENDING.value)
    
    metadata = Column(JSON, nullable=True)
    delivery_channel = Column(String(50), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    delivery_logs = relationship("DeliveryLog", back_populates="notification")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "subject": self.subject,
            "message": self.message,
            "is_read": self.is_read,
            "delivery_status": self.delivery_status,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class NotificationPreference(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    in_app_notifications = Column(Boolean, default=True)
    
    digest_emails = Column(Boolean, default=True)
    digest_frequency = Column(String(50), default="daily")
    
    unsubscribed_from = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryLog(Base):
    """Track notification delivery attempts."""
    __tablename__ = "delivery_logs"
    
    __table_args__ = (
        Index('idx_delivery_notification', 'notification_id'),
        Index('idx_delivery_status', 'status'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String(36), ForeignKey('notifications.id'), nullable=False)
    
    channel = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    
    attempt_number = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    notification = relationship("Notification", back_populates="delivery_logs")
