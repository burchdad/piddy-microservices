"""
Task Queue Service - FastAPI Routes

Background task scheduling, execution, and monitoring.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON, Enum as SqlEnum, Index, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid
import enum
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Database
DATABASE_URL = os.getenv("DATABASE_URL_TASKQUEUE", "postgresql://piddy:piddy_secure_pwd@localhost:5432/piddy_taskqueue")
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
    logger.info("Task Queue database initialized")


# Models
class TaskStatusEnum(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_priority', 'priority'),
        Index('idx_task_created', 'created_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String(100), nullable=False)
    status = Column(SqlEnum(TaskStatusEnum), default=TaskStatusEnum.PENDING)
    priority = Column(Integer, default=5)  # 1=urgent, 10=low
    payload = Column(JSON, nullable=False)
    metadata = Column(JSON)
    result = Column(JSON)
    error_message = Column(Text)
    
    scheduled_for = Column(DateTime)  # When to run
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecurringTask(Base):
    __tablename__ = "recurring_tasks"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String(100), nullable=False)
    schedule_cron = Column(String(100), nullable=False)  # Cron format
    payload = Column(JSON, nullable=False)
    active = Column(Boolean, default=True)
    last_executed = Column(DateTime)
    next_execution = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Schemas
class CreateTaskRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    priority: int = Field(5, ge=1, le=10)
    scheduled_for: Optional[datetime] = None
    max_retries: int = Field(3, ge=0, le=10)


class TaskResponse(BaseModel):
    id: str
    task_type: str
    status: str
    priority: int
    created_at: datetime


class CreateRecurringTaskRequest(BaseModel):
    task_type: str
    schedule_cron: str
    payload: Dict[str, Any]


# FastAPI App
app = FastAPI(
    title="Piddy Task Queue Service",
    description="Background task scheduling and execution",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    init_db()
    logger.info("Task Queue Service started")


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/tasks", response_model=TaskResponse)
def create_task(req: CreateTaskRequest, db: SessionLocal = Depends(get_db)):
    """Create a new background task"""
    try:
        task = Task(
            task_type=req.task_type,
            payload=req.payload,
            priority=req.priority,
            scheduled_for=req.scheduled_for or datetime.utcnow(),
            max_retries=req.max_retries,
            status=TaskStatusEnum.QUEUED,
        )
        db.add(task)
        db.commit()
        logger.info(f"Task {task.id} created: {req.task_type}")
        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: SessionLocal = Depends(get_db)):
    """Get task details and status"""
    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "result": task.result,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@app.get("/tasks")
def list_tasks(status: str = Query(None), limit: int = Query(20), db: SessionLocal = Depends(get_db)):
    """List tasks with optional status filter"""
    query = db.query(Task)
    if status:
        query = query.filter_by(status=status)
    tasks = query.order_by(Task.priority, Task.created_at).limit(limit).all()
    return {
        "tasks": [
            {
                "id": str(t.id),
                "task_type": t.task_type,
                "status": t.status,
                "priority": t.priority,
            }
            for t in tasks
        ]
    }


@app.post("/tasks/{task_id}/cancel", response_model=dict)
def cancel_task(task_id: str, db: SessionLocal = Depends(get_db)):
    """Cancel a pending task"""
    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed task")
    
    task.status = TaskStatusEnum.CANCELLED
    db.commit()
    logger.info(f"Task {task_id} cancelled")
    return {"status": "cancelled"}


@app.post("/recurring", response_model=dict)
def create_recurring_task(req: CreateRecurringTaskRequest, db: SessionLocal = Depends(get_db)):
    """Create a recurring background task"""
    try:
        recurring = RecurringTask(
            task_type=req.task_type,
            schedule_cron=req.schedule_cron,
            payload=req.payload,
        )
        db.add(recurring)
        db.commit()
        return {"id": str(recurring.id), "task_type": req.task_type, "schedule": req.schedule_cron}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create recurring task")


@app.get("/metrics")
def metrics(db: SessionLocal = Depends(get_db)):
    """Get task queue metrics"""
    total = db.query(Task).count()
    pending = db.query(Task).filter_by(status=TaskStatusEnum.PENDING).count()
    running = db.query(Task).filter_by(status=TaskStatusEnum.RUNNING).count()
    completed = db.query(Task).filter_by(status=TaskStatusEnum.COMPLETED).count()
    failed = db.query(Task).filter_by(status=TaskStatusEnum.FAILED).count()
    
    return {
        "total_tasks": total,
        "pending": pending,
        "running": running,
        "completed": completed,
        "failed": failed,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
