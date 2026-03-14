"""
Event Bus Service - FastAPI Routes

Asynchronous event publishing and subscription with persistence and replay.
"""

from fastapi import FastAPI, Depends, HTTPException,status, Query
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON, Enum as SqlEnum, Index, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import enum
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL_EVENTBUS", "postgresql://piddy:piddy_secure_pwd@localhost:5432/piddy_eventbus")
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
    logger.info("Event Bus database initialized")


# Models
class EventStatusEnum(str, enum.Enum):
    PUBLISHED = "published"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index('idx_event_type', 'event_type'),
        Index('idx_event_timestamp', 'timestamp'),
        Index('idx_event_status', 'status'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    data = Column(JSON, nullable=False)
    metadata = Column(JSON)
    status = Column(SqlEnum(EventStatusEnum), default=EventStatusEnum.PUBLISHED)
    timestamp = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    retry_count = Column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index('idx_sub_event', 'event_type'),
        Index('idx_sub_subscriber', 'subscriber_id'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    subscriber_id = Column(String(255), nullable=False)
    handler_url = Column(String(500), nullable=False)
    filter_rules = Column(JSON)  # Optional filtering
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventLog(Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index('idx_log_event', 'event_id'),
        Index('idx_log_subscriber', 'subscriber_id'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(PG_UUID(as_uuid=True), nullable=False)
    subscriber_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    attempt = Column(Integer, default=1)
    response_code = Column(Integer)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Schemas
class PublishEventRequest(BaseModel):
    event_type: str
    source: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class SubscribeRequest(BaseModel):
    event_type: str
    handler_url: str
    filter_rules: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    id: str
    event_type: str
    source: str
    timestamp: datetime
    status: str


# FastAPI App
app = FastAPI(
    title="Piddy Event Bus Service",
    description="Event publishing and subscription with persistence",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    init_db()
    logger.info("Event Bus Service started")


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/publish", response_model=dict)
def publish_event(req: PublishEventRequest, db: SessionLocal = Depends(get_db)):
    """Publish an event to the bus"""
    try:
        event = Event(
            event_type=req.event_type,
            source=req.source,
            data=req.data,
            metadata=req.metadata,
        )
        db.add(event)
        db.commit()
        logger.info(f"Event {event.id} published: {req.event_type}")
        return {"event_id": str(event.id), "status": "published"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish event")


@app.post("/subscribe", response_model=dict)
def subscribe(req: SubscribeRequest, subscriber_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """Subscribe to events"""
    try:
        sub = Subscription(
            event_type=req.event_type,
            subscriber_id=subscriber_id,
            handler_url=req.handler_url,
            filter_rules=req.filter_rules,
        )
        db.add(sub)
        db.commit()
        logger.info(f"Subscriber {subscriber_id} subscribed to {req.event_type}")
        return {"subscription_id": str(sub.id), "status": "subscribed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@app.get("/events")
def get_events(event_type: str = Query(None), limit: int = Query(20), db: SessionLocal = Depends(get_db)):
    """Get recent events"""
    query = db.query(Event)
    if event_type:
        query = query.filter_by(event_type=event_type)
    events = query.order_by(Event.timestamp.desc()).limit(limit).all()
    return {
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp.isoformat(),
                "status": e.status,
            }
            for e in events
        ]
    }


@app.get("/metrics")
def metrics(db: SessionLocal = Depends(get_db)):
    """Get event bus metrics"""
    total_events = db.query(Event).count()
    total_subscriptions = db.query(Subscription).count()
    active_subscriptions = db.query(Subscription).filter_by(active=True).count()
    return {
        "total_events": total_events,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
