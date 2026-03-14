"""
Report Builder Service - Dynamic report generation, scheduling, export
Port: 8000 (standard)
Host Port: 8118
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/piddy_report_builder")
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class ReportTemplate(Base):
    __tablename__ = "report_template"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    owner_id = Column(Integer, index=True)
    template_config = Column(Text)  # JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('report_template.id'))
    title = Column(String, index=True)
    creator_id = Column(Integer, index=True)
    status = Column(String, default="draft")  # draft, generating, ready, failed
    output_format = Column(String)  # pdf, csv, excel, html
    file_path = Column(String)
    file_size = Column(Integer, default=0)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReportSchedule(Base):
    __tablename__ = "report_schedule"
    id = Column(Integer, primary_key=True, index=True)
    report_template_id = Column(Integer, ForeignKey('report_template.id'))
    name = Column(String)
    frequency = Column(String)  # daily, weekly, monthly
    recipients = Column(Text)  # JSON list of emails
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReportDataSource(Base):
    __tablename__ = "report_data_source"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('report_template.id'))
    source_type = Column(String)  # database, api, file
    source_config = Column(Text)  # JSON config
    query_or_endpoint = Column(Text)
    cache_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReportMetrics(Base):
    __tablename__ = "report_metrics"
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey('report.id'))
    metric_name = Column(String, index=True)
    metric_value = Column(Float)
    dimension = Column(String)  # for grouping
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class TemplateCreate(BaseModel):
    name: str
    description: str
    owner_id: int
    template_config: dict = {}

class ReportCreate(BaseModel):
    template_id: int
    title: str
    creator_id: int
    output_format: str = "pdf"

class ReportScheduleCreate(BaseModel):
    template_id: int
    name: str
    frequency: str  # daily, weekly, monthly
    recipients: List[str]

class DataSourceCreate(BaseModel):
    template_id: int
    source_type: str
    source_config: dict
    query_or_endpoint: str

# FastAPI App
app = FastAPI(title="Report Builder Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "report-builder",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(template: TemplateCreate, db=Depends(get_db)):
    """Create report template"""
    db_template = ReportTemplate(
        name=template.name,
        description=template.description,
        owner_id=template.owner_id,
        template_config=json.dumps(template.template_config)
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.get("/templates/{template_id}")
async def get_template(template_id: int, db=Depends(get_db)):
    """Get report template"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@app.get("/templates")
async def list_templates(owner_id: int = None, db=Depends(get_db)):
    """List report templates"""
    query = db.query(ReportTemplate)
    if owner_id:
        query = query.filter(ReportTemplate.owner_id == owner_id)
    templates = query.limit(50).all()
    return templates

@app.post("/templates/{template_id}/data-sources", status_code=status.HTTP_201_CREATED)
async def add_data_source(template_id: int, ds: DataSourceCreate, db=Depends(get_db)):
    """Add data source to template"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db_ds = ReportDataSource(
        template_id=template_id,
        source_type=ds.source_type,
        source_config=json.dumps(ds.source_config),
        query_or_endpoint=ds.query_or_endpoint
    )
    db.add(db_ds)
    db.commit()
    db.refresh(db_ds)
    return db_ds

@app.post("/reports", status_code=status.HTTP_201_CREATED)
async def generate_report(
    report: ReportCreate,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Generate new report"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == report.template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db_report = Report(
        template_id=report.template_id,
        title=report.title,
        creator_id=report.creator_id,
        status="generating",
        output_format=report.output_format
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # Schedule background generation
    background_tasks.add_task(generate_report_background, db_report.id)
    
    return {
        "report_id": db_report.id,
        "status": "generating",
        "output_format": report.output_format
    }

def generate_report_background(report_id: int):
    """Background task to generate report"""
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return
        
        # Simulate report generation
        import time
        time.sleep(1)  # Simulate processing
        
        report.status = "ready"
        report.file_path = f"reports/{report_id}/report.{report.output_format}"
        report.file_size = 1024 * 50  # 50 KB simulated
        report.execution_time_ms = 1500
        db.commit()
    finally:
        db.close()

@app.get("/reports/{report_id}")
async def get_report(report_id: int, db=Depends(get_db)):
    """Get report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "title": report.title,
        "status": report.status,
        "output_format": report.output_format,
        "file_path": report.file_path,
        "file_size": report.file_size,
        "execution_time_ms": report.execution_time_ms,
        "created_at": report.created_at
    }

@app.get("/reports")
async def list_reports(creator_id: int = None, status: str = None, db=Depends(get_db)):
    """List reports"""
    query = db.query(Report)
    if creator_id:
        query = query.filter(Report.creator_id == creator_id)
    if status:
        query = query.filter(Report.status == status)
    
    reports = query.order_by(Report.created_at.desc()).limit(50).all()
    return reports

@app.post("/reports/{report_id}/export")
async def export_report(report_id: int, export_format: str, db=Depends(get_db)):
    """Export report to different format"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != "ready":
        raise HTTPException(status_code=400, detail="Report not ready for export")
    
    if export_format not in ["pdf", "csv", "excel", "html"]:
        raise HTTPException(status_code=400, detail="Invalid export format")
    
    return {
        "report_id": report_id,
        "format": export_format,
        "export_path": f"exports/{report_id}/export.{export_format}",
        "exported_at": datetime.utcnow().isoformat()
    }

@app.post("/schedules", status_code=status.HTTP_201_CREATED)
async def schedule_report(schedule: ReportScheduleCreate, db=Depends(get_db)):
    """Schedule recurring report generation"""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == schedule.template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if schedule.frequency not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    
    next_run = datetime.utcnow() + timedelta(days=1)
    
    db_schedule = ReportSchedule(
        report_template_id=schedule.template_id,
        name=schedule.name,
        frequency=schedule.frequency,
        recipients=json.dumps(schedule.recipients),
        next_run=next_run
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return {
        "schedule_id": db_schedule.id,
        "name": schedule.name,
        "frequency": schedule.frequency,
        "next_run": next_run,
        "recipients": schedule.recipients
    }

@app.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: int, db=Depends(get_db)):
    """Get report schedule"""
    schedule = db.query(ReportSchedule).filter(
        ReportSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {
        "id": schedule.id,
        "name": schedule.name,
        "frequency": schedule.frequency,
        "recipients": json.loads(schedule.recipients),
        "enabled": schedule.enabled,
        "next_run": schedule.next_run
    }

@app.get("/metrics")
async def get_service_metrics(db=Depends(get_db)):
    """Get service metrics"""
    template_count = db.query(ReportTemplate).count()
    report_count = db.query(Report).count()
    schedule_count = db.query(ReportSchedule).count()
    ready_reports = db.query(Report).filter(Report.status == "ready").count()
    
    return {
        "templates": template_count,
        "reports_generated": report_count,
        "schedules_active": schedule_count,
        "reports_ready": ready_reports,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
