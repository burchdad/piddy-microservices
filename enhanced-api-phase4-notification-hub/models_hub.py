"""
Notification Hub Service - Database Models

Data models for notification routing, channels, and delivery tracking.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Enum, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from database_hub import Base


class NotificationChannelEnum(str, enum.Enum):
    """Supported notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriorityEnum(str, enum.Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatusEnum(str, enum.Enum):
    """Notification delivery status"""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPreset(Base):
    """Template for commonly used notifications"""
    __tablename__ = "notification_presets"
    __table_args__ = (
        Index('idx_preset_name', 'name'),
        Index('idx_preset_category', 'category'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)
    channels = Column(JSON, nullable=False)  # List of channels to use
    template_data = Column(JSON, nullable=False)  # Subject, body, etc.
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationRoute(Base):
    """Route configuration for different notification types"""
    __tablename__ = "notification_routes"
    __table_args__ = (
        Index('idx_route_type_user', 'notification_type', 'user_id'),
        Index('idx_route_active', 'active'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    notification_type = Column(String(100), nullable=False)
    
    # Primary channel for this notification type
    primary_channel = Column(Enum(NotificationChannelEnum), default=NotificationChannelEnum.EMAIL)
    
    # Fallback channels (ordered)
    fallback_channels = Column(JSON)  # List of channels to try if primary fails
    
    # Routing rules
    enabled = Column(Boolean, default=True)
    batch_notifications = Column(Boolean, default=False)  # Batch multiple notifications
    batch_window_seconds = Column(Integer, default=3600)  # Window for batching
    rate_limit_per_hour = Column(Integer, default=0)  # 0 = unlimited
    
    # Delivery preferences
    quiet_hours_start = Column(String(5))  # HH:MM format
    quiet_hours_end = Column(String(5))
    timezone = Column(String(100), default="UTC")
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HubNotification(Base):
    """Central notification record for tracking"""
    __tablename__ = "hub_notifications"
    __table_args__ = (
        Index('idx_hub_user_type', 'user_id', 'notification_type'),
        Index('idx_hub_status', 'status'),
        Index('idx_hub_created', 'created_at'),
        Index('idx_hub_channel', 'channel'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    notification_type = Column(String(100), nullable=False)
    
    # Content
    title = Column(String(255))
    body = Column(Text, nullable=False)
    data = Column(JSON)  # Additional metadata
    
    # Routing info
    channel = Column(Enum(NotificationChannelEnum), nullable=False)
    priority = Column(Enum(NotificationPriorityEnum), default=NotificationPriorityEnum.MEDIUM)
    
    # Status tracking
    status = Column(Enum(NotificationStatusEnum), default=NotificationStatusEnum.PENDING)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    failed_reason = Column(Text)
    
    # Linked service IDs
    email_service_id = Column(UUID(as_uuid=True))
    sms_service_id = Column(UUID(as_uuid=True))
    push_service_id = Column(UUID(as_uuid=True))
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime)
    
    # Source info
    source = Column(String(100))  # Which service created this notification
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationBatch(Base):
    """Group related notifications for batch delivery"""
    __tablename__ = "notification_batches"
    __table_args__ = (
        Index('idx_batch_user', 'user_id'),
        Index('idx_batch_status', 'status'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    notification_type = Column(String(100), nullable=False)
    channel = Column(Enum(NotificationChannelEnum), nullable=False)
    
    # Batch content
    title = Column(String(255))  # Batch title
    notifications = Column(JSON)  # List of notification IDs/content
    count = Column(Integer, default=0)
    
    # Batch status
    status = Column(Enum(NotificationStatusEnum), default=NotificationStatusEnum.PENDING)
    sent_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationMetrics(Base):
    """Track notification metrics and analytics"""
    __tablename__ = "notification_metrics"
    __table_args__ = (
        Index('idx_metrics_date', 'metric_date'),
        Index('idx_metrics_type', 'notification_type'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date = Column(DateTime, nullable=False)
    
    # Breakdown by type and channel
    notification_type = Column(String(100), nullable=False)
    channel = Column(Enum(NotificationChannelEnum), nullable=False)
    
    # Metrics
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    avg_delivery_time_ms = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationChannel(Base):
    """Service channels registered with the hub"""
    __tablename__ = "notification_channels"
    __table_args__ = (
        Index('idx_channel_type', 'channel_type'),
        Index('idx_channel_active', 'active'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_type = Column(Enum(NotificationChannelEnum), nullable=False, unique=True)
    
    # Service endpoint details
    service_url = Column(String(500), nullable=False)
    service_health_url = Column(String(500))
    
    # Credentials
    api_key = Column(String(500))  # Encrypted in production
    additional_config = Column(JSON)  # Custom config per channel
    
    # Status
    active = Column(Boolean, default=True)
    health_status = Column(String(50), default="unknown")
    last_health_check = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
