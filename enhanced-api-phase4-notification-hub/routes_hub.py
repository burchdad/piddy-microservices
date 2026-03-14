"""
Notification Hub Service - FastAPI Routes

Central notification routing, batching, scheduling, and delivery tracking.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import os
import uuid
import asyncio
import httpx

from database_hub import get_db, init_db
from models_hub import (
    NotificationChannelEnum,
    NotificationPriorityEnum,
    NotificationStatusEnum,
    NotificationPreset,
    NotificationRoute,
    HubNotification,
    NotificationBatch,
    NotificationMetrics,
    NotificationChannel,
)
from pydantic_models_hub import (
    SendNotificationRequest,
    SendNotificationResponse,
    NotificationStatusResponse,
    BatchNotificationRequest,
    BatchNotificationResponse,
    NotificationRouteRequest,
    NotificationRouteResponse,
    ListRoutesResponse,
    NotificationPresetRequest,
    NotificationPresetResponse,
    SendFromPresetRequest,
    ListPresetsResponse,
    RegisterChannelRequest,
    ChannelHealthResponse,
    ListChannelsResponse,
    MetricsRequest,
    MetricsResponse,
    ListMetricsResponse,
    UserNotificationPreferencesRequest,
    UserPreferencesResponse,
    HealthCheckResponse,
    ErrorResponse,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Piddy Notification Hub Service",
    description="Central notification routing and delivery management",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Startup/Shutdown
@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Notification Hub Service started")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Notification Hub Service stopped")


# ============================================================================
# Health & Monitoring
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Check service health"""
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

    channel_count = db.query(NotificationChannel).filter_by(active=True).count()

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        database=db_status,
        channels=channel_count,
        timestamp=datetime.utcnow(),
        uptime_seconds=0,
    )


@app.get("/metrics", response_model=dict, tags=["Health"])
def service_metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    total_notifications = db.query(HubNotification).count()
    delivered = db.query(HubNotification).filter_by(
        status=NotificationStatusEnum.DELIVERED
    ).count()
    failed = db.query(HubNotification).filter_by(
        status=NotificationStatusEnum.FAILED
    ).count()
    pending = db.query(HubNotification).filter_by(
        status=NotificationStatusEnum.PENDING
    ).count()

    return {
        "total_notifications": total_notifications,
        "delivered": delivered,
        "failed": failed,
        "pending": pending,
        "success_rate": (delivered / total_notifications * 100) if total_notifications > 0 else 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Notification Sending
# ============================================================================

@app.post("/send", response_model=SendNotificationResponse, tags=["Notifications"])
async def send_notification(
    request: SendNotificationRequest,
    db: Session = Depends(get_db),
):
    """Send a notification through the hub"""
    try:
        # Get user's notification route if it exists
        route = db.query(NotificationRoute).filter(
            NotificationRoute.user_id == request.user_id,
            NotificationRoute.notification_type == request.notification_type,
        ).first()

        # Determine channel
        channel = request.channel or (route.primary_channel if route else NotificationChannelEnum.EMAIL)

        # Create notification record
        notification = HubNotification(
            user_id=request.user_id,
            notification_type=request.notification_type,
            title=request.title,
            body=request.body,
            data=request.data,
            channel=channel,
            priority=request.priority,
            status=NotificationStatusEnum.QUEUED,
            source=request.source,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        logger.info(f"Notification {notification.id} queued for {request.user_id}")

        return SendNotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            notification_type=notification.notification_type,
            channel=notification.channel,
            status=notification.status,
            created_at=notification.created_at,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue notification",
        )


@app.post("/batch", response_model=BatchNotificationResponse, tags=["Notifications"])
async def send_batch_notifications(
    request: BatchNotificationRequest,
    db: Session = Depends(get_db),
):
    """Send multiple notifications as a batch"""
    try:
        notification_ids = []

        # Create individual notifications
        for notif in request.notifications:
            notification = HubNotification(
                user_id=request.user_id,
                notification_type=notif.notification_type,
                title=notif.title,
                body=notif.body,
                data=notif.data,
                channel=notif.channel or NotificationChannelEnum.EMAIL,
                priority=notif.priority,
                status=NotificationStatusEnum.QUEUED,
                source=notif.source,
            )
            db.add(notification)
            notification_ids.append(notification.id)

        # Create batch record
        batch = NotificationBatch(
            user_id=request.user_id,
            notification_type=request.notification_type,
            channel=NotificationChannelEnum.EMAIL,
            title=request.batch_title,
            notifications=notification_ids,
            count=len(notification_ids),
            status=NotificationStatusEnum.QUEUED,
        )

        db.add(batch)
        db.commit()
        db.refresh(batch)

        logger.info(f"Batch {batch.id} created with {len(notification_ids)} notifications")

        return BatchNotificationResponse(
            batch_id=batch.id,
            notification_count=batch.count,
            created_at=batch.created_at,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to send batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch",
        )


# ============================================================================
# Notification Status & Management
# ============================================================================

@app.get("/notifications/{notification_id}", response_model=NotificationStatusResponse, tags=["Notifications"])
def get_notification_status(
    notification_id: str = Path(..., description="Notification ID"),
    db: Session = Depends(get_db),
):
    """Get status of a specific notification"""
    notification = db.query(HubNotification).filter_by(id=notification_id).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationStatusResponse(
        id=notification.id,
        status=notification.status,
        channel=notification.channel,
        sent_at=notification.sent_at,
        delivered_at=notification.delivered_at,
        failed_reason=notification.failed_reason,
        retry_count=notification.retry_count,
    )


@app.get("/users/{user_id}/notifications", response_model=dict, tags=["Notifications"])
def get_user_notifications(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str = Query(None),
    db: Session = Depends(get_db),
):
    """Get notification history for a user"""
    query = db.query(HubNotification).filter_by(user_id=user_id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    total = query.count()
    notifications = query.order_by(HubNotification.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "notifications": [
            {
                "id": str(n.id),
                "status": n.status,
                "channel": n.channel,
                "created_at": n.created_at.isoformat(),
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
            }
            for n in notifications
        ],
    }


# ============================================================================
# Routing Configuration
# ============================================================================

@app.post("/routes", response_model=NotificationRouteResponse, tags=["Routes"])
def create_notification_route(
    request: NotificationRouteRequest,
    db: Session = Depends(get_db),
):
    """Create or update a notification route for a user"""
    try:
        route = db.query(NotificationRoute).filter(
            NotificationRoute.user_id == request.user_id,
            NotificationRoute.notification_type == request.notification_type,
        ).first()

        if route:
            # Update existing
            route.primary_channel = request.primary_channel
            route.fallback_channels = request.fallback_channels
            route.enabled = request.enabled
            route.batch_notifications = request.batch_notifications
            route.batch_window_seconds = request.batch_window_seconds
            route.rate_limit_per_hour = request.rate_limit_per_hour
            route.quiet_hours_start = request.quiet_hours_start
            route.quiet_hours_end = request.quiet_hours_end
            route.timezone = request.timezone
            route.updated_at = datetime.utcnow()
        else:
            # Create new
            route = NotificationRoute(
                user_id=request.user_id,
                notification_type=request.notification_type,
                primary_channel=request.primary_channel,
                fallback_channels=request.fallback_channels,
                enabled=request.enabled,
                batch_notifications=request.batch_notifications,
                batch_window_seconds=request.batch_window_seconds,
                rate_limit_per_hour=request.rate_limit_per_hour,
                quiet_hours_start=request.quiet_hours_start,
                quiet_hours_end=request.quiet_hours_end,
                timezone=request.timezone,
            )

        db.add(route)
        db.commit()
        db.refresh(route)

        return NotificationRouteResponse(
            id=route.id,
            user_id=route.user_id,
            notification_type=route.notification_type,
            primary_channel=route.primary_channel,
            fallback_channels=route.fallback_channels,
            enabled=route.enabled,
            batch_notifications=route.batch_notifications,
            batch_window_seconds=route.batch_window_seconds,
            rate_limit_per_hour=route.rate_limit_per_hour,
            quiet_hours_start=route.quiet_hours_start,
            quiet_hours_end=route.quiet_hours_end,
            timezone=route.timezone,
            created_at=route.created_at,
            updated_at=route.updated_at,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification route",
        )


@app.get("/routes/{user_id}", response_model=ListRoutesResponse, tags=["Routes"])
def get_user_routes(
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get all notification routes for a user"""
    routes = db.query(NotificationRoute).filter_by(user_id=user_id).all()

    return ListRoutesResponse(
        routes=[
            NotificationRouteResponse(
                id=r.id,
                user_id=r.user_id,
                notification_type=r.notification_type,
                primary_channel=r.primary_channel,
                fallback_channels=r.fallback_channels,
                enabled=r.enabled,
                batch_notifications=r.batch_notifications,
                batch_window_seconds=r.batch_window_seconds,
                rate_limit_per_hour=r.rate_limit_per_hour,
                quiet_hours_start=r.quiet_hours_start,
                quiet_hours_end=r.quiet_hours_end,
                timezone=r.timezone,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in routes
        ],
        total=len(routes),
    )


# ============================================================================
# Channel Management
# ============================================================================

@app.post("/channels", response_model=dict, tags=["Channels"])
def register_channel(
    request: RegisterChannelRequest,
    db: Session = Depends(get_db),
):
    """Register a notification channel service"""
    try:
        channel = db.query(NotificationChannel).filter_by(channel_type=request.channel_type).first()

        if channel:
            channel.service_url = str(request.service_url)
            channel.service_health_url = str(request.service_health_url) if request.service_health_url else None
            channel.api_key = request.api_key
            channel.additional_config = request.additional_config
            channel.updated_at = datetime.utcnow()
        else:
            channel = NotificationChannel(
                channel_type=request.channel_type,
                service_url=str(request.service_url),
                service_health_url=str(request.service_health_url) if request.service_health_url else None,
                api_key=request.api_key,
                additional_config=request.additional_config,
            )

        db.add(channel)
        db.commit()
        db.refresh(channel)

        return {
            "id": str(channel.id),
            "channel_type": channel.channel_type,
            "active": channel.active,
            "created_at": channel.created_at.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register channel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register channel",
        )


@app.get("/channels", response_model=ListChannelsResponse, tags=["Channels"])
def get_channels(db: Session = Depends(get_db)):
    """Get all registered channels and their health status"""
    channels = db.query(NotificationChannel).all()

    return ListChannelsResponse(
        channels=[
            ChannelHealthResponse(
                channel_type=c.channel_type,
                health_status=c.health_status,
                last_health_check=c.last_health_check,
                active=c.active,
            )
            for c in channels
        ],
        total=len(channels),
    )


# ============================================================================
# Presets/Templates
# ============================================================================

@app.post("/presets", response_model=NotificationPresetResponse, tags=["Presets"])
def create_preset(
    request: NotificationPresetRequest,
    db: Session = Depends(get_db),
):
    """Create a notification preset/template"""
    try:
        preset = NotificationPreset(
            name=request.name,
            category=request.category,
            channels=request.channels,
            template_data=request.template_data,
            description=request.description,
        )

        db.add(preset)
        db.commit()
        db.refresh(preset)

        return NotificationPresetResponse(
            id=preset.id,
            name=preset.name,
            category=preset.category,
            channels=preset.channels,
            template_data=preset.template_data,
            description=preset.description,
            active=preset.active,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create preset",
        )


@app.get("/presets", response_model=ListPresetsResponse, tags=["Presets"])
def get_presets(
    category: str = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get notification presets"""
    query = db.query(NotificationPreset)

    if active_only:
        query = query.filter_by(active=True)

    if category:
        query = query.filter_by(category=category)

    presets = query.all()

    return ListPresetsResponse(
        presets=[
            NotificationPresetResponse(
                id=p.id,
                name=p.name,
                category=p.category,
                channels=p.channels,
                template_data=p.template_data,
                description=p.description,
                active=p.active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in presets
        ],
        total=len(presets),
    )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
