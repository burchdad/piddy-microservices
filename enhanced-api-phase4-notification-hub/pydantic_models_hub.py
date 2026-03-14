"""
Notification Hub Service - Pydantic Schemas

Request and response models for API validation.
"""

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID


class ChannelEnum(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class PriorityEnum(str, Enum):
    """Priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class StatusEnum(str, Enum):
    """Notification status"""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Notification Request/Response
# ============================================================================

class SendNotificationRequest(BaseModel):
    """Request to send a notification through the hub"""
    user_id: str = Field(..., description="Target user ID")
    notification_type: str = Field(..., description="Type of notification (e.g., 'order_shipped')")
    title: Optional[str] = Field("", description="Notification title")
    body: str = Field(..., description="Notification body/content")
    channel: Optional[ChannelEnum] = Field(None, description="Override preferred channel")
    priority: PriorityEnum = Field(PriorityEnum.MEDIUM, description="Delivery priority")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data/context")
    source: Optional[str] = Field("system", description="Source service that triggered this")


class SendNotificationResponse(BaseModel):
    """Response after sending notification"""
    id: UUID
    user_id: str
    notification_type: str
    channel: ChannelEnum
    status: StatusEnum
    created_at: datetime


class NotificationStatusRequest(BaseModel):
    """Request to check notification status"""
    notification_id: UUID


class NotificationStatusResponse(BaseModel):
    """Notification status response"""
    id: UUID
    status: StatusEnum
    channel: ChannelEnum
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed_reason: Optional[str]
    retry_count: int


class BatchNotificationRequest(BaseModel):
    """Request to send batched notifications"""
    user_id: str
    notification_type: str
    notifications: List[SendNotificationRequest] = Field(..., min_items=1)
    batch_title: Optional[str] = None


class BatchNotificationResponse(BaseModel):
    """Response for batch notification"""
    batch_id: UUID
    notification_count: int
    created_at: datetime


# ============================================================================
# Routing Configuration
# ============================================================================

class NotificationRouteRequest(BaseModel):
    """Create/update notification route"""
    user_id: str
    notification_type: str
    primary_channel: ChannelEnum = ChannelEnum.EMAIL
    fallback_channels: Optional[List[ChannelEnum]] = None
    enabled: bool = True
    batch_notifications: bool = False
    batch_window_seconds: int = 3600
    rate_limit_per_hour: int = 0
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str = "UTC"


class NotificationRouteResponse(BaseModel):
    """Notification route response"""
    id: UUID
    user_id: str
    notification_type: str
    primary_channel: ChannelEnum
    fallback_channels: Optional[List[ChannelEnum]]
    enabled: bool
    batch_notifications: bool
    batch_window_seconds: int
    rate_limit_per_hour: int
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    timezone: str
    created_at: datetime
    updated_at: datetime


class ListRoutesResponse(BaseModel):
    """List of notification routes"""
    routes: List[NotificationRouteResponse]
    total: int


# ============================================================================
# Presets (Templates)
# ============================================================================

class NotificationPresetRequest(BaseModel):
    """Create notification preset/template"""
    name: str = Field(..., description="Unique preset name")
    category: str = Field(..., description="Preset category")
    channels: List[ChannelEnum] = Field(..., description="Default channels")
    template_data: Dict[str, Any] = Field(..., description="Template content")
    description: Optional[str] = None


class NotificationPresetResponse(BaseModel):
    """Notification preset response"""
    id: UUID
    name: str
    category: str
    channels: List[ChannelEnum]
    template_data: Dict[str, Any]
    description: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime


class SendFromPresetRequest(BaseModel):
    """Send notification using a preset template"""
    user_id: str
    preset_name: str
    template_variables: Optional[Dict[str, Any]] = None
    priority: PriorityEnum = PriorityEnum.MEDIUM


class ListPresetsResponse(BaseModel):
    """List of presets"""
    presets: List[NotificationPresetResponse]
    total: int


# ============================================================================
# Channel Management
# ============================================================================

class RegisterChannelRequest(BaseModel):
    """Register a notification channel service"""
    channel_type: ChannelEnum
    service_url: HttpUrl = Field(..., description="Base URL of service")
    service_health_url: Optional[HttpUrl] = None
    api_key: Optional[str] = None
    additional_config: Optional[Dict[str, Any]] = None


class ChannelHealthResponse(BaseModel):
    """Health status of a channel"""
    channel_type: ChannelEnum
    health_status: str
    last_health_check: Optional[datetime]
    active: bool


class ListChannelsResponse(BaseModel):
    """List of registered channels"""
    channels: List[ChannelHealthResponse]
    total: int


# ============================================================================
# Metrics & Analytics
# ============================================================================

class MetricsRequest(BaseModel):
    """Request metrics for a time period"""
    notification_type: Optional[str] = None
    channel: Optional[ChannelEnum] = None
    days: int = Field(7, ge=1, le=90, description="Number of days to retrieve")


class MetricsResponse(BaseModel):
    """Notification metrics"""
    metric_date: datetime
    notification_type: str
    channel: ChannelEnum
    sent_count: int
    delivered_count: int
    failed_count: int
    avg_delivery_time_ms: int
    delivery_rate: float


class ListMetricsResponse(BaseModel):
    """List of metrics"""
    metrics: List[MetricsResponse]


# ============================================================================
# User Preferences
# ============================================================================

class UserNotificationPreferencesRequest(BaseModel):
    """User notification preferences"""
    user_id: str
    unsubscribe_all: bool = False
    notification_types: Dict[str, bool] = Field(
        ..., 
        description="Per-type opt-in/out"
    )
    channel_preferences: Dict[ChannelEnum, bool] = Field(
        ..., 
        description="Per-channel opt-in/out"
    )
    do_not_disturb: bool = False
    do_not_disturb_start: Optional[str] = None
    do_not_disturb_end: Optional[str] = None


class UserPreferencesResponse(BaseModel):
    """User preferences response"""
    user_id: str
    unsubscribe_all: bool
    notification_types: Dict[str, bool]
    channel_preferences: Dict[ChannelEnum, bool]
    do_not_disturb: bool
    do_not_disturb_start: Optional[str]
    do_not_disturb_end: Optional[str]
    updated_at: datetime


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    status_code: int
    timestamp: datetime


# ============================================================================
# Health Check
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Service health status"""
    status: str
    version: str
    database: str
    channels: int
    timestamp: datetime
    uptime_seconds: int
