"""
Phase 2: Pydantic Models - Request/Response Schemas

Full API contract models for notification service.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Notification delivery types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class DeliveryStatus(str, Enum):
    """Delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationBase(BaseModel):
    """Base notification model."""
    
    user_id: str = Field(..., min_length=1, max_length=36)
    notification_type: str
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    """Create notification request."""
    pass


class NotificationResponse(NotificationBase):
    """Notification response model."""
    
    id: str
    is_read: bool
    delivery_status: str = DeliveryStatus.PENDING.value
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List notifications response."""
    
    user_id: str
    total: int
    notifications: List[NotificationResponse]
    
    class Config:
        from_attributes = True


class NotificationPreferenceBase(BaseModel):
    """Base notification preferences."""
    
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    in_app_notifications: bool = True
    
    digest_emails: bool = True
    digest_frequency: str = Field("daily", regex="^(daily|weekly|monthly)$")
    
    unsubscribed_from: Optional[Dict[str, bool]] = None


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    """Update preferences request."""
    pass


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Preferences response."""
    
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeliveryLogEntry(BaseModel):
    """Delivery attempt log."""
    
    id: str
    notification_id: str
    channel: str
    status: str
    attempt_number: int
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    
    class Config:
        from_attributes = True


class BulkNotificationRequest(BaseModel):
    """Send notification to multiple users."""
    
    user_ids: List[str] = Field(..., min_items=1, max_items=1000)
    notification_type: str
    subject: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        """Validate user IDs are non-empty."""
        if not all(uid for uid in v):
            raise ValueError("User IDs cannot be empty")
        return v


class NotificationTemplate(BaseModel):
    """Reusable notification template."""
    
    id: str
    name: str
    subject_template: str
    message_template: str
    notification_type: str
    variables: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class ServiceMetrics(BaseModel):
    """Service health and performance metrics."""
    
    service: str = "notification-service"
    uptime_seconds: int
    notifications_sent: int
    notifications_failed: int
    queue_length: int
    active_workers: int
    avg_delivery_time_ms: float
    timestamp: datetime
