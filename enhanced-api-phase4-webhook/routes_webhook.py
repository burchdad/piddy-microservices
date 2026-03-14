"""
Webhook Service - FastAPI Routes

Third-party webhook management, delivery, retry logic, and event subscriptions.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime
import uuid
import enum
import logging
import os
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Database
DATABASE_URL = os.getenv("DATABASE_URL_WEBHOOK", "postgresql://piddy:piddy_secure_pwd@localhost:5432/piddy_webhook")
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Webhook database initialized")


# Models
class WebhookEventEnum(str, enum.Enum):
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    PAYMENT_COMPLETED = "payment.completed"
    USER_REGISTERED = "user.registered"
    NOTIFICATION_SENT = "notification.sent"


class WebhookStatusEnum(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # List of events to subscribe
    secret = Column(String(255))  # For signing
    active = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(PG_UUID(as_uuid=True), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Enum(WebhookStatusEnum), default=WebhookStatusEnum.PENDING)
    response_status = Column(Integer)
    response_body = Column(Text)
    attempt = Column(Integer, default=1)
    next_retry = Column(DateTime)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas
class RegisterWebhookRequest(BaseModel):
    url: HttpUrl
    events: List[str]
    retry_count: int = Field(3, ge=0, le=10)


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    events: List[str]
    active: bool
    created_at: datetime


class PublishEventRequest(BaseModel):
    event_type: str
    data: Dict[str, Any]


# FastAPI App
app = FastAPI(
    title="Piddy Webhook Service",
    description="Webhook registration, delivery, and event subscriptions",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    init_db()
    logger.info("Webhook Service started")


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/webhooks", response_model=dict)
def register_webhook(req: RegisterWebhookRequest, owner_id: str = Query(...), db: Session = Depends(get_db)):
    """Register a webhook"""
    try:
        webhook = Webhook(
            owner_id=owner_id,
            url=str(req.url),
            events=req.events,
            secret=str(uuid.uuid4()),
            retry_count=req.retry_count,
        )
        db.add(webhook)
        db.commit()
        return {"id": str(webhook.id), "url": webhook.url, "secret": webhook.secret}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to register webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to register webhook")


@app.get("/webhooks")
def list_webhooks(owner_id: str = Query(...), db: Session = Depends(get_db)):
    """List webhooks for owner"""
    webhooks = db.query(Webhook).filter_by(owner_id=owner_id, active=True).all()
    return {"webhooks": [{"id": str(w.id), "url": w.url, "events": w.events} for w in webhooks]}


@app.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str, db: Session = Depends(get_db)):
    """Delete a webhook"""
    webhook = db.query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook.active = False
    db.commit()
    return {"status": "deleted"}


@app.post("/events")
async def publish_event(req: PublishEventRequest, db: Session = Depends(get_db)):
    """Publish an event to subscribed webhooks"""
    try:
        webhooks = db.query(Webhook).filter(Webhook.active == True).all()
        for webhook in webhooks:
            if req.event_type in webhook.events:
                delivery = WebhookDelivery(
                    webhook_id=webhook.id,
                    event_type=req.event_type,
                    payload=req.data,
                    status=WebhookStatusEnum.PENDING,
                )
                db.add(delivery)
        db.commit()
        return {"status": "published", "event_type": req.event_type}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get webhook metrics"""
    total_webhooks = db.query(Webhook).count()
    total_deliveries = db.query(WebhookDelivery).count()
    successful = db.query(WebhookDelivery).filter_by(status=WebhookStatusEnum.DELIVERED).count()
    return {
        "total_webhooks": total_webhooks,
        "total_deliveries": total_deliveries,
        "successful_deliveries": successful,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
