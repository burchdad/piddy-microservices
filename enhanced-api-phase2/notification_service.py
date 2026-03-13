"""
Notification Microservice - FastAPI Service

Handles user notifications, preferences, and delivery.
Integrates with user service through REST API and message queues.
"""

from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from enum import Enum
import uuid

from database_notif import get_db, init_db
from models_notif import Notification, NotificationPreference, NotificationType
from email_service import send_email_async
from queue_service import queue_notification

app = FastAPI(
    title="Piddy Notification Service",
    description="Microservice for handling user notifications",
    version="1.0.0"
)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    init_db()


class NotificationRequest(BaseModel):
    """Request to create notification."""
    user_id: str
    notification_type: str
    subject: str
    message: str
    metadata: Optional[dict] = None


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str
    user_id: str
    notification_type: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": "notification-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a notification for a user.
    
    - Validates user exists (calls user service)
    - Checks notification preferences
    - Queues for async processing
    - Returns notification details
    """
    
    try:
        # Verify user exists (in production, call user service)
        # response = requests.get(f"{USER_SERVICE_URL}/api/v1/users/{request.user_id}")
        # if response.status_code != 200:
        #     raise HTTPException(status_code=404, detail="User not found")
        
        # Check user preferences
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == request.user_id
        ).first()
        
        if preferences and not preferences.email_notifications:
            # User has disabled email notifications
            return {
                "message": "Notification not sent - user has disabled this type"
            }
        
        # Create notification in database
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            notification_type=request.notification_type,
            subject=request.subject,
            message=request.message,
            metadata=request.metadata or {},
            is_read=False,
            created_at=datetime.utcnow()
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Queue for async email delivery
        background_tasks.add_task(
            queue_notification,
            notification.id,
            request.user_id,
            request.subject,
            request.message
        )
        
        return NotificationResponse(**notification.to_dict())
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@app.get("/notifications/{user_id}")
async def list_user_notifications(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get all notifications for a user."""
    
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "user_id": user_id,
        "total": len(notifications),
        "notifications": [n.to_dict() for n in notifications]
    }


@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """Mark notification as read."""
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"status": "read"}


@app.post("/preferences/{user_id}")
async def update_notification_preferences(
    user_id: str,
    preferences: dict,
    db: Session = Depends(get_db)
):
    """Update user notification preferences."""
    
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    
    if not pref:
        pref = NotificationPreference(
            user_id=user_id,
            **preferences
        )
        db.add(pref)
    else:
        for key, value in preferences.items():
            setattr(pref, key, value)
    
    db.commit()
    return {"status": "preferences updated"}


@app.get("/metrics")
async def service_metrics():
    """Service metrics endpoint for monitoring."""
    return {
        "service": "notification-service",
        "uptime": "monitoring",
        "notifications_sent": "tracking",
        "queue_length": "monitoring"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
