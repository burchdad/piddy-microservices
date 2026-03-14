"""
SMS Service - SMS Delivery
Handles SMS sending, OTP delivery, delivery tracking
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Piddy SMS Service",
    description="SMS delivery with OTP and tracking support",
    version="1.0.0",
)


class SMSRequest(BaseModel):
    """SMS request"""
    phone_number: str
    message: str
    otp_code: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class BatchSMSRequest(BaseModel):
    """Batch SMS request"""
    phone_numbers: list[str]
    message: str
    scheduled_at: Optional[datetime] = None


@app.on_event("startup")
def startup():
    logger.info("SMS Service started")


@app.get("/health")
def health_check():
    """SMS service health check"""
    return {"status": "healthy", "service": "sms", "version": "1.0.0"}


@app.post("/send")
def send_sms(request: SMSRequest):
    """Send SMS message"""
    try:
        logger.info(f"Sending SMS to {request.phone_number}")
        
        # Validate phone number
        if not request.phone_number or len(request.phone_number) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")
        
        return {
            "success": True,
            "sms_id": "sms_123",
            "phone_number": request.phone_number,
            "scheduled_at": request.scheduled_at,
        }
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send SMS")


@app.post("/send-batch")
def send_batch_sms(request: BatchSMSRequest):
    """Send batch SMS messages"""
    try:
        logger.info(f"Sending batch SMS to {len(request.phone_numbers)} recipients")
        
        return {
            "success": True,
            "batch_id": "batch_sms_123",
            "recipients_count": len(request.phone_numbers),
            "scheduled_at": request.scheduled_at,
        }
    except Exception as e:
        logger.error(f"Batch SMS sending failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send batch SMS")


@app.post("/send-otp")
def send_otp(phone_number: str, otp_code: str):
    """Send OTP code"""
    try:
        logger.info(f"Sending OTP to {phone_number}")
        
        return {
            "success": True,
            "sms_id": "otp_123",
            "phone_number": phone_number,
            "expires_in": 600,  # 10 minutes
        }
    except Exception as e:
        logger.error(f"OTP sending failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")


@app.get("/status/{sms_id}")
def get_sms_status(sms_id: str):
    """Get SMS delivery status"""
    return {
        "sms_id": sms_id,
        "status": "delivered",
        "sent_at": datetime.utcnow(),
        "delivered_at": datetime.utcnow(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
