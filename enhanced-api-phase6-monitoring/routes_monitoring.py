"""
Monitoring & Alerts Service - Health monitoring, alerting, dashboards
Port: 8000 (standard)
Host Port: 8115
"""
import os
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_monitoring")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class MonitoringTarget(Base):
    __tablename__ = "monitoring_targets"
    id = Column(Integer, primary_key=True, index=True)
    target_name = Column(String(200), unique=True)
    target_type = Column(String(50))  # service, endpoint, database, host
    target_url = Column(String(500))
    health_check_interval = Column(Integer, default=60)  # seconds
    timeout = Column(Integer, default=10)  # seconds
    is_active = Column(Boolean, default=True)
    group = Column(String(100))
    metadata = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class HealthCheck(Base):
    __tablename__ = "health_checks"
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, index=True)
    status = Column(String(50))  # healthy, degraded, unhealthy
    response_time = Column(Float)
    status_code = Column(Integer)
    error_message = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_target_checked', 'target_id', 'checked_at'),
    )

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    metric_type = Column(String(50))  # cpu, memory, disk, latency, requests, errors
    unit = Column(String(50))
    threshold = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_target_metric', 'target_id', 'metric_name'),
    )

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(100), unique=True)
    target_id = Column(Integer, index=True)
    alert_type = Column(String(100))  # threshold_exceeded, service_down, high_latency, high_error_rate
    severity = Column(String(50), default="warning")  # critical, high, medium, low
    title = Column(String(500))
    description = Column(Text)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    threshold_value = Column(Float)
    status = Column(String(50), default="active")  # active, acknowledged, resolved, ignored
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    acknowledged_by = Column(String(100))
    
    __table_args__ = (
        Index('idx_status_severity', 'status', 'severity'),
    )

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(200))
    rule_type = Column(String(100))  # threshold, anomaly, composite
    target_id = Column(Integer, index=True)
    metric_name = Column(String(200))
    condition = Column(String(50))  # gt, lt, eq, gte, lte
    threshold = Column(Float)
    duration = Column(Integer)  # seconds condition must be true
    is_active = Column(Boolean, default=True)
    actions = Column(Text, default="[]")  # JSON array of actions
    created_at = Column(DateTime, default=datetime.utcnow)

class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    id = Column(Integer, primary_key=True, index=True)
    channel_name = Column(String(200))
    channel_type = Column(String(50))  # email, slack, pagerduty, webhook
    configuration = Column(Text)  # JSON config
    is_active = Column(Boolean, default=True)
    alert_filter = Column(Text, default="{}")  # JSON filter for which alerts to send
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertNotification(Base):
    __tablename__ = "alert_notifications"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, index=True)
    channel_id = Column(Integer, index=True)
    status = Column(String(50), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Dashboard(Base):
    __tablename__ = "dashboards"
    id = Column(Integer, primary_key=True, index=True)
    dashboard_name = Column(String(200))
    owner_id = Column(String(100))
    layout = Column(Text, default="[]")
    widgets = Column(Text, default="[]")
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class TargetCreate(BaseModel):
    target_name: str
    target_type: str
    target_url: str
    health_check_interval: int = 60
    group: str = None

class MetricCreate(BaseModel):
    target_id: int
    metric_name: str
    metric_value: float
    metric_type: str
    unit: str = None
    threshold: float = None

class AlertRuleCreate(BaseModel):
    rule_name: str
    target_id: int
    metric_name: str
    condition: str
    threshold: float
    duration: int = 300

class NotificationChannelCreate(BaseModel):
    channel_name: str
    channel_type: str
    configuration: dict
    alert_filter: dict = Field(default=None)

class DashboardCreate(BaseModel):
    dashboard_name: str
    owner_id: str
    layout: list = Field(default=None)
    widgets: list = Field(default=None)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Monitoring & Alerts Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    targets = db.query(MonitoringTarget).count()
    active_alerts = db.query(Alert).filter(Alert.status == "active").count()
    rules = db.query(AlertRule).count()
    
    return {
        "total_targets": targets,
        "active_alerts": active_alerts,
        "total_rules": rules,
        "timestamp": datetime.utcnow()
    }

# Monitoring Target Endpoints
@app.post("/targets")
def create_target(target: TargetCreate, db: Session = Depends(get_db)):
    """Create monitoring target"""
    db_target = MonitoringTarget(
        target_name=target.target_name,
        target_type=target.target_type,
        target_url=target.target_url,
        health_check_interval=target.health_check_interval,
        group=target.group
    )
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    
    return {
        "id": db_target.id,
        "target_name": db_target.target_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/targets")
def list_targets(group: str = Query(None), db: Session = Depends(get_db)):
    """List monitoring targets"""
    query = db.query(MonitoringTarget).filter(MonitoringTarget.is_active == True)
    
    if group:
        query = query.filter(MonitoringTarget.group == group)
    
    targets = query.all()
    
    return {
        "total": len(targets),
        "targets": targets,
        "timestamp": datetime.utcnow()
    }

@app.get("/targets/{target_id}/status")
def get_target_status(target_id: int, db: Session = Depends(get_db)):
    """Get target current status"""
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    latest_check = db.query(HealthCheck).filter(
        HealthCheck.target_id == target_id
    ).order_by(HealthCheck.checked_at.desc()).first()
    
    return {
        "target_id": target_id,
        "target_name": target.target_name,
        "status": latest_check.status if latest_check else "unknown",
        "response_time": latest_check.response_time if latest_check else None,
        "last_check": latest_check.checked_at if latest_check else None,
        "timestamp": datetime.utcnow()
    }

# Health Check Endpoints
@app.post("/targets/{target_id}/health-check")
def record_health_check(
    target_id: int,
    status: str,
    response_time: float,
    status_code: int = None,
    error_message: str = None,
    db: Session = Depends(get_db)
):
    """Record health check result"""
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    db_check = HealthCheck(
        target_id=target_id,
        status=status,
        response_time=response_time,
        status_code=status_code,
        error_message=error_message
    )
    db.add(db_check)
    db.commit()
    
    return {
        "target_id": target_id,
        "status": status,
        "response_time": response_time,
        "timestamp": datetime.utcnow()
    }

# Metrics Endpoints
@app.post("/targets/{target_id}/metrics")
def record_metric(target_id: int, metric: MetricCreate, db: Session = Depends(get_db)):
    """Record metric"""
    db_metric = Metric(
        target_id=target_id,
        metric_name=metric.metric_name,
        metric_value=metric.metric_value,
        metric_type=metric.metric_type,
        unit=metric.unit,
        threshold=metric.threshold
    )
    db.add(db_metric)
    db.commit()
    
    return {
        "id": db_metric.id,
        "metric_name": metric.metric_name,
        "metric_value": metric.metric_value,
        "status": "recorded",
        "timestamp": datetime.utcnow()
    }

@app.get("/targets/{target_id}/metrics/{metric_name}")
def get_metric_history(
    target_id: int,
    metric_name: str,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """Get metric history"""
    metrics = db.query(Metric).filter(
        Metric.target_id == target_id,
        Metric.metric_name == metric_name
    ).order_by(Metric.recorded_at.desc()).limit(limit).all()
    
    return {
        "target_id": target_id,
        "metric_name": metric_name,
        "data_points": len(metrics),
        "metrics": metrics,
        "timestamp": datetime.utcnow()
    }

# Alert Endpoints
@app.get("/alerts")
def list_alerts(
    status: str = Query(None),
    severity: str = Query(None),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db)
):
    """List alerts"""
    query = db.query(Alert)
    
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()
    
    return {
        "total": query.count(),
        "alerts": alerts,
        "timestamp": datetime.utcnow()
    }

@app.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, acknowledged_by: str, db: Session = Depends(get_db)):
    """Acknowledge alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = acknowledged_by
    db.commit()
    
    return {
        "alert_id": alert_id,
        "status": "acknowledged",
        "timestamp": datetime.utcnow()
    }

@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Resolve alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()
    
    return {
        "alert_id": alert_id,
        "status": "resolved",
        "timestamp": datetime.utcnow()
    }

# Alert Rule Endpoints
@app.post("/alert-rules")
def create_alert_rule(rule: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create alert rule"""
    db_rule = AlertRule(
        rule_name=rule.rule_name,
        target_id=rule.target_id,
        metric_name=rule.metric_name,
        condition=rule.condition,
        threshold=rule.threshold,
        duration=rule.duration
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return {
        "id": db_rule.id,
        "rule_name": db_rule.rule_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/alert-rules")
def list_alert_rules(db: Session = Depends(get_db)):
    """List alert rules"""
    rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()
    
    return {
        "total": len(rules),
        "rules": rules,
        "timestamp": datetime.utcnow()
    }

# Dashboard Endpoints
@app.post("/dashboards")
def create_dashboard(dashboard: DashboardCreate, db: Session = Depends(get_db)):
    """Create dashboard"""
    db_dashboard = Dashboard(
        dashboard_name=dashboard.dashboard_name,
        owner_id=dashboard.owner_id,
        layout=json.dumps(dashboard.layout) if dashboard.layout else "[]",
        widgets=json.dumps(dashboard.widgets) if dashboard.widgets else "[]"
    )
    db.add(db_dashboard)
    db.commit()
    db.refresh(db_dashboard)
    
    return {
        "id": db_dashboard.id,
        "dashboard_name": db_dashboard.dashboard_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/dashboards")
def list_dashboards(owner_id: str = Query(None), db: Session = Depends(get_db)):
    """List dashboards"""
    query = db.query(Dashboard)
    
    if owner_id:
        query = query.filter(Dashboard.owner_id == owner_id)
    
    dashboards = query.all()
    
    return {
        "total": len(dashboards),
        "dashboards": dashboards,
        "timestamp": datetime.utcnow()
    }

# Summary Endpoints
@app.get("/status/summary")
def get_status_summary(db: Session = Depends(get_db)):
    """Get overall system status summary"""
    total_targets = db.query(MonitoringTarget).count()
    healthy_targets = db.query(HealthCheck).filter(
        HealthCheck.status == "healthy"
    ).count()
    active_alerts = db.query(Alert).filter(Alert.status == "active").count()
    
    return {
        "total_targets": total_targets,
        "healthy_targets": healthy_targets,
        "degraded_targets": total_targets - healthy_targets,
        "active_alerts": active_alerts,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
