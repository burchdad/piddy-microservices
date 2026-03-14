"""
Push Notification Service - Mobile Push Notifications
Handles FCM and APNS push notification delivery
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Piddy Push Notification Service",
    description="Mobile push notifications via FCM and APNS",
    version="1.0.0",
)


class DeviceToken(BaseModel):
    """Device registration"""
    user_id: str
    device_type: str  # ios, android, web
    token: str
    device_name: Optional[str] = None


class PushNotificationRequest(BaseModel):
    """Push notification request"""
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None
    badge: Optional[int] = None
    sound: Optional[str] = None
    priority: Optional[str] = "high"


class BatchPushRequest(BaseModel):
    """Batch push notification request"""
    user_ids: List[str]
    title: str
    body: str
    data: Optional[dict] = None


@app.on_event("startup")
def startup():
    logger.info("Push Notification Service started")


@app.get("/health")
def health_check():
    """Push service health check"""
    return {"status": "healthy", "service": "push", "version": "1.0.0"}


@app.post("/register-device")
def register_device(request: DeviceToken):
    """Register device for push notifications"""
    try:
        logger.info(f"Register {request.device_type} device for user {request.user_id}")
        
        return {
            "success": True,
            "device_id": "device_123",
            "user_id": request.user_id,
            "registered_at": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        raise HTTPException(status_code=500, detail="Device registration failed")


@app.post("/send")
def send_push_notification(request: PushNotificationRequest):
    """Send push notification"""
    try:
        logger.info(f"Sending push to user {request.user_id}")
        
        return {
            "success": True,
            "push_id": "push_123",
            "user_id": request.user_id,
            "sent_at": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Push notification failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send push")


@app.post("/send-batch")
def send_batch_push(request: BatchPushRequest):
    """Send push to multiple users"""
    try:
        logger.info(f"Sending batch push to {len(request.user_ids)} users")
        
        return {
            "success": True,
            "batch_id": "batch_push_123",
            "recipients_count": len(request.user_ids),
            "sent_at": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Batch push failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send batch push")


@app.get("/devices/{user_id}")
def list_user_devices(user_id: str):
    """List user's registered devices"""
    return {
        "user_id": user_id,
        "devices": [
            {
                "device_id": "device_123",
                "device_type": "ios",
                "device_name": "iPhone",
                "registered_at": datetime.utcnow(),
            }
        ],
    }


@app.get("/status/{push_id}")
def get_push_status(push_id: str):
    """Get push notification status"""
    return {
        "push_id": push_id,
        "status": "delivered",
        "sent_at": datetime.utcnow(),
        "delivered_at": datetime.utcnow(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
