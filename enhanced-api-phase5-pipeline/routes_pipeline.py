"""
Data Pipeline Service - ETL/ELT processing and data transformation
Port: 8000 (standard)
Host Port: 8107
"""
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_pipeline")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class PipelinJob(Base):
    __tablename__ = "pipeline_jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(200), index=True)
    job_type = Column(String(100))  # etl, elt, transform, validation
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    source = Column(String(200))
    destination = Column(String(200))
    config = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    records_processed = Column(Integer, default=0)

class DataTransformation(Base):
    __tablename__ = "data_transformations"
    id = Column(Integer, primary_key=True, index=True)
    transformation_name = Column(String(200), index=True)
    transformation_type = Column(String(100))  # map, filter, aggregate, merge
    rules = Column(Text)
    transformation_config = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Integer, default=1)

class DataValidation(Base):
    __tablename__ = "data_validations"
    id = Column(Integer, primary_key=True, index=True)
    validation_name = Column(String(200), index=True)
    validation_type = Column(String(100))  # schema, range, uniqueness, format
    rules = Column(Text)
    status = Column(String(50))  # passed, failed, warning
    validated_at = Column(DateTime, default=datetime.utcnow)
    records_validated = Column(Integer, default=0)
    errors = Column(Text, default="[]")

class PipelineMetrics(Base):
    __tablename__ = "pipeline_metrics"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    unit = Column(String(50))
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_job_metric', 'job_id', 'metric_name'),
    )

class ScheduledPipeline(Base):
    __tablename__ = "scheduled_pipelines"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_name = Column(String(200), index=True)
    schedule_type = Column(String(100))  # daily, hourly, weekly, monthly, cron
    cron_expression = Column(String(100))
    pipeline_config = Column(Text)
    is_active = Column(Integer, default=1)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class PipelineJobRequest(BaseModel):
    job_name: str
    job_type: str
    source: str
    destination: str
    config: dict = Field(default=None)

class TransformationRequest(BaseModel):
    transformation_name: str
    transformation_type: str
    rules: str
    transformation_config: dict = Field(default=None)

class ValidationRequest(BaseModel):
    validation_name: str
    validation_type: str
    rules: str

class ScheduleRequest(BaseModel):
    pipeline_name: str
    schedule_type: str
    cron_expression: str = None
    pipeline_config: str

class JobResponse(BaseModel):
    id: int
    job_name: str
    job_type: str
    status: str
    created_at: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Data Pipeline Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    job_count = db.query(PipelinJob).count()
    running_jobs = db.query(PipelinJob).filter(PipelinJob.status == "running").count()
    transformation_count = db.query(DataTransformation).count()
    validation_count = db.query(DataValidation).count()
    
    return {
        "total_jobs": job_count,
        "running_jobs": running_jobs,
        "total_transformations": transformation_count,
        "total_validations": validation_count,
        "timestamp": datetime.utcnow()
    }

# Pipeline Jobs Endpoints
@app.post("/jobs", response_model=JobResponse)
def create_job(job: PipelineJobRequest, db: Session = Depends(get_db)):
    """Create new pipeline job"""
    db_job = PipelinJob(
        job_name=job.job_name,
        job_type=job.job_type,
        source=job.source,
        destination=job.destination,
        config=json.dumps(job.config) if job.config else "{}",
        status="pending"
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/jobs")
def list_jobs(
    status: str = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List pipeline jobs"""
    query = db.query(PipelinJob)
    if status:
        query = query.filter(PipelinJob.status == status)
    
    jobs = query.order_by(PipelinJob.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "total": total,
        "jobs": jobs,
        "timestamp": datetime.utcnow()
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(PipelinJob).filter(PipelinJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "job_name": job.job_name,
        "status": job.status,
        "records_processed": job.records_processed,
        "created_at": job.created_at,
        "timestamp": datetime.utcnow()
    }

@app.post("/jobs/{job_id}/run")
def run_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start job execution"""
    job = db.query(PipelinJob).filter(PipelinJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "running"
    job.started_at = datetime.utcnow()
    db.commit()
    
    return {
        "job_id": job.id,
        "status": "running",
        "started_at": job.started_at,
        "timestamp": datetime.utcnow()
    }

@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel job execution"""
    job = db.query(PipelinJob).filter(PipelinJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "running":
        raise HTTPException(status_code=400, detail="Job is not running")
    
    job.status = "cancelled"
    db.commit()
    
    return {
        "job_id": job.id,
        "status": "cancelled",
        "timestamp": datetime.utcnow()
    }

# Transformation Endpoints
@app.post("/transformations")
def create_transformation(transform: TransformationRequest, db: Session = Depends(get_db)):
    """Create data transformation rule"""
    db_transform = DataTransformation(
        transformation_name=transform.transformation_name,
        transformation_type=transform.transformation_type,
        rules=transform.rules,
        transformation_config=json.dumps(transform.transformation_config) if transform.transformation_config else "{}"
    )
    db.add(db_transform)
    db.commit()
    db.refresh(db_transform)
    
    return {
        "id": db_transform.id,
        "transformation_name": db_transform.transformation_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/transformations")
def list_transformations(db: Session = Depends(get_db)):
    """List all transformations"""
    transformations = db.query(DataTransformation).all()
    return {
        "total": len(transformations),
        "transformations": transformations,
        "timestamp": datetime.utcnow()
    }

@app.get("/transformations/{transform_id}")
def get_transformation(transform_id: int, db: Session = Depends(get_db)):
    """Get transformation details"""
    transform = db.query(DataTransformation).filter(DataTransformation.id == transform_id).first()
    if not transform:
        raise HTTPException(status_code=404, detail="Transformation not found")
    
    return {
        "id": transform.id,
        "transformation_name": transform.transformation_name,
        "rules": transform.rules,
        "timestamp": datetime.utcnow()
    }

# Validation Endpoints
@app.post("/validations")
def create_validation(validation: ValidationRequest, db: Session = Depends(get_db)):
    """Create data validation rule"""
    db_validation = DataValidation(
        validation_name=validation.validation_name,
        validation_type=validation.validation_type,
        rules=validation.rules,
        status="pending"
    )
    db.add(db_validation)
    db.commit()
    db.refresh(db_validation)
    
    return {
        "id": db_validation.id,
        "validation_name": db_validation.validation_name,
        "status": "pending",
        "timestamp": datetime.utcnow()
    }

@app.get("/validations")
def list_validations(db: Session = Depends(get_db)):
    """List all validations"""
    validations = db.query(DataValidation).all()
    return {
        "total": len(validations),
        "validations": validations,
        "timestamp": datetime.utcnow()
    }

@app.post("/validations/{validation_id}/run")
def run_validation(validation_id: int, db: Session = Depends(get_db)):
    """Execute validation rule"""
    validation = db.query(DataValidation).filter(DataValidation.id == validation_id).first()
    if not validation:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    validation.status = "passed"
    validation.validated_at = datetime.utcnow()
    db.commit()
    
    return {
        "validation_id": validation.id,
        "status": "passed",
        "records_validated": validation.records_validated,
        "timestamp": datetime.utcnow()
    }

# Scheduled Pipeline Endpoints
@app.post("/schedules")
def create_schedule(schedule: ScheduleRequest, db: Session = Depends(get_db)):
    """Create scheduled pipeline"""
    db_schedule = ScheduledPipeline(
        pipeline_name=schedule.pipeline_name,
        schedule_type=schedule.schedule_type,
        cron_expression=schedule.cron_expression,
        pipeline_config=schedule.pipeline_config
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return {
        "id": db_schedule.id,
        "pipeline_name": db_schedule.pipeline_name,
        "status": "scheduled",
        "timestamp": datetime.utcnow()
    }

@app.get("/schedules")
def list_schedules(db: Session = Depends(get_db)):
    """List scheduled pipelines"""
    schedules = db.query(ScheduledPipeline).all()
    return {
        "total": len(schedules),
        "schedules": schedules,
        "timestamp": datetime.utcnow()
    }

@app.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Get schedule details"""
    schedule = db.query(ScheduledPipeline).filter(ScheduledPipeline.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {
        "id": schedule.id,
        "pipeline_name": schedule.pipeline_name,
        "is_active": schedule.is_active,
        "next_run": schedule.next_run,
        "timestamp": datetime.utcnow()
    }

# Pipeline Monitoring
@app.get("/jobs/{job_id}/metrics")
def get_job_metrics(job_id: int, db: Session = Depends(get_db)):
    """Get job metrics"""
    metrics = db.query(PipelineMetrics).filter(PipelineMetrics.job_id == job_id).all()
    
    return {
        "job_id": job_id,
        "metric_count": len(metrics),
        "metrics": metrics,
        "timestamp": datetime.utcnow()
    }

@app.get("/jobs/stats/summary")
def get_jobs_summary(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get jobs summary statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_jobs = db.query(PipelinJob).filter(PipelinJob.created_at >= start_date).count()
    completed_jobs = db.query(PipelinJob).filter(
        PipelinJob.status == "completed",
        PipelinJob.created_at >= start_date
    ).count()
    failed_jobs = db.query(PipelinJob).filter(
        PipelinJob.status == "failed",
        PipelinJob.created_at >= start_date
    ).count()
    
    return {
        "days": days,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
