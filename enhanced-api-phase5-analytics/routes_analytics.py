"""
Analytics Service - Event ingestion, metrics aggregation, and reporting
Port: 8000 (standard)
Host Port: 8105
"""
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_analytics")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class EventLog(Base):
    __tablename__ = "event_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True)
    event_type = Column(String(100), index=True)
    event_name = Column(String(200))
    properties = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String(100))
    
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_event_timestamp', 'event_type', 'timestamp'),
    )

class MetricAggregation(Base):
    __tablename__ = "metric_aggregations"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200), index=True)
    metric_type = Column(String(50))  # count, sum, average, max, min
    value = Column(Float)
    label = Column(String(100))  # daily, hourly, weekly
    unit = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class UserSegment(Base):
    __tablename__ = "user_segments"
    id = Column(Integer, primary_key=True, index=True)
    segment_name = Column(String(200), index=True)
    segment_type = Column(String(100))  # cohort, behavior, demographic
    criteria = Column(Text)
    user_count = Column(Integer, default=0)
    properties = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class CustomReport(Base):
    __tablename__ = "custom_reports"
    id = Column(Integer, primary_key=True, index=True)
    report_name = Column(String(200))
    report_type = Column(String(100))  # dashboard, export, scheduled
    query_config = Column(Text)
    filters = Column(Text, default="{}")
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_at = Column(DateTime)
    status = Column(String(50), default="pending")  # pending, completed, failed

class AnalyticsMetrics(Base):
    __tablename__ = "analytics_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200), index=True)
    metric_value = Column(Float)
    dimension = Column(String(200))
    tags = Column(Text, default="{}")
    recorded_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class EventRequest(BaseModel):
    user_id: str
    event_type: str
    event_name: str
    properties: dict = Field(default=None)
    session_id: str = None

class MetricRequest(BaseModel):
    metric_name: str
    metric_type: str
    value: float
    label: str = None
    unit: str = None

class SegmentRequest(BaseModel):
    segment_name: str
    segment_type: str
    criteria: str
    properties: dict = Field(default=None)

class ReportRequest(BaseModel):
    report_name: str
    report_type: str
    query_config: str
    filters: dict = Field(default=None)

class EventResponse(BaseModel):
    id: int
    user_id: str
    event_type: str
    event_name: str
    timestamp: datetime

class MetricResponse(BaseModel):
    id: int
    metric_name: str
    metric_type: str
    value: float
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Analytics Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    event_count = db.query(EventLog).count()
    metric_count = db.query(MetricAggregation).count()
    segment_count = db.query(UserSegment).count()
    
    return {
        "total_events": event_count,
        "total_metrics": metric_count,
        "total_segments": segment_count,
        "timestamp": datetime.utcnow()
    }

# Events Endpoints
@app.post("/events", response_model=EventResponse)
def ingest_event(event: EventRequest, db: Session = Depends(get_db)):
    """Ingest a new event"""
    db_event = EventLog(
        user_id=event.user_id,
        event_type=event.event_type,
        event_name=event.event_name,
        properties=json.dumps(event.properties) if event.properties else "{}",
        session_id=event.session_id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.post("/events/batch")
def batch_ingest_events(events: list[EventRequest], db: Session = Depends(get_db)):
    """Batch ingest multiple events"""
    db_events = [
        EventLog(
            user_id=event.user_id,
            event_type=event.event_type,
            event_name=event.event_name,
            properties=json.dumps(event.properties) if event.properties else "{}",
            session_id=event.session_id
        )
        for event in events
    ]
    db.add_all(db_events)
    db.commit()
    return {
        "ingested": len(db_events),
        "timestamp": datetime.utcnow()
    }

@app.get("/events/user/{user_id}")
def get_user_events(
    user_id: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get events for a specific user"""
    events = db.query(EventLog).filter(
        EventLog.user_id == user_id
    ).order_by(
        EventLog.timestamp.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "user_id": user_id,
        "count": len(events),
        "events": events,
        "timestamp": datetime.utcnow()
    }

@app.get("/events/type/{event_type}")
def get_events_by_type(
    event_type: str,
    days: int = Query(7, le=90),
    db: Session = Depends(get_db)
):
    """Get events by type for last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    events = db.query(EventLog).filter(
        EventLog.event_type == event_type,
        EventLog.timestamp >= start_date
    ).all()
    
    return {
        "event_type": event_type,
        "days": days,
        "count": len(events),
        "timestamp": datetime.utcnow()
    }

# Metrics Endpoints
@app.post("/metrics", response_model=MetricResponse)
def record_metric(metric: MetricRequest, db: Session = Depends(get_db)):
    """Record a new metric"""
    db_metric = MetricAggregation(
        metric_name=metric.metric_name,
        metric_type=metric.metric_type,
        value=metric.value,
        label=metric.label,
        unit=metric.unit
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric

@app.get("/metrics/summary")
def get_metrics_summary(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get metrics summary"""
    start_date = datetime.utcnow() - timedelta(days=days)
    metrics = db.query(MetricAggregation).filter(
        MetricAggregation.timestamp >= start_date
    ).all()
    
    return {
        "total_metrics": len(metrics),
        "days": days,
        "metrics": metrics,
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics/{metric_name}")
def get_metric_series(
    metric_name: str,
    days: int = Query(7, le=90),
    db: Session = Depends(get_db)
):
    """Get time series for specific metric"""
    start_date = datetime.utcnow() - timedelta(days=days)
    series = db.query(MetricAggregation).filter(
        MetricAggregation.metric_name == metric_name,
        MetricAggregation.timestamp >= start_date
    ).order_by(MetricAggregation.timestamp).all()
    
    return {
        "metric_name": metric_name,
        "data_points": len(series),
        "series": series,
        "timestamp": datetime.utcnow()
    }

# Segments Endpoints
@app.post("/segments")
def create_segment(segment: SegmentRequest, db: Session = Depends(get_db)):
    """Create user segment"""
    db_segment = UserSegment(
        segment_name=segment.segment_name,
        segment_type=segment.segment_type,
        criteria=segment.criteria,
        properties=json.dumps(segment.properties) if segment.properties else "{}"
    )
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    
    return {
        "id": db_segment.id,
        "segment_name": db_segment.segment_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/segments")
def list_segments(db: Session = Depends(get_db)):
    """List all user segments"""
    segments = db.query(UserSegment).all()
    return {
        "total": len(segments),
        "segments": segments,
        "timestamp": datetime.utcnow()
    }

@app.get("/segments/{segment_id}")
def get_segment(segment_id: int, db: Session = Depends(get_db)):
    """Get segment details and members"""
    segment = db.query(UserSegment).filter(UserSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return {
        "id": segment.id,
        "segment_name": segment.segment_name,
        "user_count": segment.user_count,
        "properties": json.loads(segment.properties),
        "timestamp": datetime.utcnow()
    }

# Reports Endpoints
@app.post("/reports")
def create_report(report: ReportRequest, db: Session = Depends(get_db)):
    """Create custom report"""
    db_report = CustomReport(
        report_name=report.report_name,
        report_type=report.report_type,
        query_config=report.query_config,
        filters=json.dumps(report.filters) if report.filters else "{}",
        created_by="system",
        status="pending"
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return {
        "id": db_report.id,
        "report_name": db_report.report_name,
        "status": "pending",
        "timestamp": datetime.utcnow()
    }

@app.get("/reports")
def list_reports(db: Session = Depends(get_db)):
    """List all reports"""
    reports = db.query(CustomReport).order_by(CustomReport.created_at.desc()).all()
    return {
        "total": len(reports),
        "reports": reports,
        "timestamp": datetime.utcnow()
    }

@app.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get report details"""
    report = db.query(CustomReport).filter(CustomReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "report_name": report.report_name,
        "status": report.status,
        "created_at": report.created_at,
        "timestamp": datetime.utcnow()
    }

# Dashboard Endpoints
@app.get("/dashboard/overview")
def get_dashboard_overview(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get dashboard overview data"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_events = db.query(EventLog).filter(EventLog.timestamp >= start_date).count()
    unique_users = db.query(EventLog.user_id).filter(
        EventLog.timestamp >= start_date
    ).distinct().count()
    total_metrics = db.query(MetricAggregation).filter(
        MetricAggregation.timestamp >= start_date
    ).count()
    
    return {
        "days": days,
        "total_events": total_events,
        "unique_users": unique_users,
        "total_metrics": total_metrics,
        "timestamp": datetime.utcnow()
    }

@app.get("/dashboard/trends")
def get_dashboard_trends(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get dashboard trends"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events_by_date = db.query(EventLog.timestamp, EventLog.event_type).filter(
        EventLog.timestamp >= start_date
    ).all()
    
    return {
        "days": days,
        "trends": len(events_by_date),
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
