"""
CRM Service - Customer relationship management, contacts, interactions
Port: 8000 (standard)
Host Port: 8112
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_crm")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(String(100), unique=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(200), index=True)
    phone = Column(String(20))
    company = Column(String(200), index=True)
    title = Column(String(200))
    status = Column(String(50), default="active")  # active, archived, inactive
    lifecycle = Column(String(50))  # lead, customer, prospect, archived
    source = Column(String(100))  # website, referral, advertisement
    tags = Column(Text, default="[]")
    custom_fields = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime)
    
    __table_args__ = (
        Index('idx_email_status', 'email', 'status'),
        Index('idx_company_lifecycle', 'company', 'lifecycle'),
    )

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, index=True)
    interaction_type = Column(String(100))  # email, call, meeting, note, task
    subject = Column(String(500))
    description = Column(Text)
    outcome = Column(String(200))  # positive, negative, neutral, pending
    related_contact = Column(Integer)
    scheduled_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_minutes = Column(Integer)
    notes = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_contact_type', 'contact_id', 'interaction_type'),
    )

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(String(100), unique=True)
    contact_id = Column(Integer, index=True)
    deal_name = Column(String(500))
    deal_stage = Column(String(50))  # prospect, qualified, negotiation, closed_won, closed_lost
    deal_value = Column(Float)
    currency = Column(String(10), default="USD")
    probability = Column(Float, default=0.0)  # 0-100
    expected_close_date = Column(DateTime)
    closed_date = Column(DateTime)
    close_reason = Column(String(200))
    assigned_to = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True)
    contact_id = Column(Integer, index=True)
    task_type = Column(String(100))  # email, call, review, follow_up
    title = Column(String(500))
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, completed, cancelled
    priority = Column(String(50), default="medium")  # low, medium, high, urgent
    due_date = Column(DateTime)
    assigned_to = Column(String(100))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_assigned_status', 'assigned_to', 'status'),
    )

class CRMAnalytics(Base):
    __tablename__ = "crm_analytics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    metric_type = Column(String(100))  # revenue, conversion, activity
    period = Column(String(50))  # daily, weekly, monthly
    recorded_at = Column(DateTime, default=datetime.utcnow)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(100), unique=True)
    company_name = Column(String(500), index=True)
    industry = Column(String(200))
    size = Column(String(50))  # small, medium, large, enterprise
    annual_revenue = Column(Float)
    website = Column(String(300))
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    contact_count = Column(Integer, default=0)
    deal_count = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
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
class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str = None
    company: str = None
    title: str = None
    source: str = None
    tags: list = Field(default=None)

class InteractionCreate(BaseModel):
    contact_id: int
    interaction_type: str
    subject: str
    description: str = None
    outcome: str = None
    scheduled_at: datetime = None

class DealCreate(BaseModel):
    contact_id: int
    deal_name: str
    deal_stage: str
    deal_value: float
    probability: float = 0.0
    expected_close_date: datetime = None

class TaskCreate(BaseModel):
    contact_id: int
    task_type: str
    title: str
    description: str = None
    priority: str = "medium"
    due_date: datetime = None
    assigned_to: str = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="CRM Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    contacts = db.query(Contact).count()
    deals = db.query(Deal).count()
    tasks = db.query(Task).count()
    interactions = db.query(Interaction).count()
    
    return {
        "total_contacts": contacts,
        "total_deals": deals,
        "total_tasks": tasks,
        "total_interactions": interactions,
        "timestamp": datetime.utcnow()
    }

# Contact Endpoints
@app.post("/contacts")
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create contact"""
    db_contact = Contact(
        contact_id=f"con_{datetime.utcnow().timestamp()}",
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone,
        company=contact.company,
        title=contact.title,
        source=contact.source,
        tags=json.dumps(contact.tags) if contact.tags else "[]"
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    
    return {
        "id": db_contact.id,
        "contact_id": db_contact.contact_id,
        "name": f"{db_contact.first_name} {db_contact.last_name}",
        "email": db_contact.email,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/contacts")
def list_contacts(
    lifecycle: str = Query(None),
    company: str = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List contacts"""
    query = db.query(Contact).filter(Contact.status == "active")
    
    if lifecycle:
        query = query.filter(Contact.lifecycle == lifecycle)
    if company:
        query = query.filter(Contact.company == company)
    
    contacts = query.offset(offset).limit(limit).all()
    
    return {
        "total": query.count(),
        "contacts": contacts,
        "timestamp": datetime.utcnow()
    }

@app.get("/contacts/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get contact details"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    interactions = db.query(Interaction).filter(Interaction.contact_id == contact_id).count()
    deals = db.query(Deal).filter(Deal.contact_id == contact_id).count()
    
    return {
        "id": contact.id,
        "name": f"{contact.first_name} {contact.last_name}",
        "email": contact.email,
        "company": contact.company,
        "lifecycle": contact.lifecycle,
        "interaction_count": interactions,
        "deal_count": deals,
        "timestamp": datetime.utcnow()
    }

@app.put("/contacts/{contact_id}")
def update_contact(contact_id: int, contact_data: ContactCreate, db: Session = Depends(get_db)):
    """Update contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact.first_name = contact_data.first_name
    contact.last_name = contact_data.last_name
    contact.email = contact_data.email
    contact.phone = contact_data.phone
    contact.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": contact.id,
        "status": "updated",
        "timestamp": datetime.utcnow()
    }

# Interaction Endpoints
@app.post("/contacts/{contact_id}/interactions")
def create_interaction(contact_id: int, interaction: InteractionCreate, db: Session = Depends(get_db)):
    """Log interaction with contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db_interaction = Interaction(
        contact_id=contact_id,
        interaction_type=interaction.interaction_type,
        subject=interaction.subject,
        description=interaction.description,
        outcome=interaction.outcome,
        scheduled_at=interaction.scheduled_at
    )
    db.add(db_interaction)
    contact.last_interaction = datetime.utcnow()
    db.commit()
    db.refresh(db_interaction)
    
    return {
        "id": db_interaction.id,
        "interaction_type": interaction.interaction_type,
        "status": "logged",
        "timestamp": datetime.utcnow()
    }

@app.get("/contacts/{contact_id}/interactions")
def get_contact_interactions(contact_id: int, db: Session = Depends(get_db)):
    """Get interaction history for contact"""
    interactions = db.query(Interaction).filter(
        Interaction.contact_id == contact_id
    ).order_by(Interaction.created_at.desc()).all()
    
    return {
        "contact_id": contact_id,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "timestamp": datetime.utcnow()
    }

# Deal Endpoints
@app.post("/contacts/{contact_id}/deals")
def create_deal(contact_id: int, deal: DealCreate, db: Session = Depends(get_db)):
    """Create deal for contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db_deal = Deal(
        deal_id=f"deal_{datetime.utcnow().timestamp()}",
        contact_id=contact_id,
        deal_name=deal.deal_name,
        deal_stage=deal.deal_stage,
        deal_value=deal.deal_value,
        probability=deal.probability,
        expected_close_date=deal.expected_close_date
    )
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    
    return {
        "id": db_deal.id,
        "deal_id": db_deal.deal_id,
        "deal_name": db_deal.deal_name,
        "deal_value": db_deal.deal_value,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/deals")
def list_deals(stage: str = Query(None), db: Session = Depends(get_db)):
    """List all deals"""
    query = db.query(Deal)
    if stage:
        query = query.filter(Deal.deal_stage == stage)
    
    deals = query.all()
    
    return {
        "total": len(deals),
        "deals": deals,
        "timestamp": datetime.utcnow()
    }

# Task Endpoints
@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create task"""
    db_task = Task(
        task_id=f"task_{datetime.utcnow().timestamp()}",
        contact_id=task.contact_id,
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        assigned_to=task.assigned_to
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return {
        "id": db_task.id,
        "task_id": db_task.task_id,
        "title": db_task.title,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/tasks")
def list_tasks(
    status: str = Query(None),
    assigned_to: str = Query(None),
    db: Session = Depends(get_db)
):
    """List tasks"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    
    tasks = query.all()
    
    return {
        "total": len(tasks),
        "tasks": tasks,
        "timestamp": datetime.utcnow()
    }

@app.put("/tasks/{task_id}")
def update_task_status(task_id: int, status: str, db: Session = Depends(get_db)):
    """Update task status"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = status
    if status == "completed":
        task.completed_at = datetime.utcnow()
    db.commit()
    
    return {
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.utcnow()
    }

# CRM Analytics
@app.get("/analytics/pipeline")
def get_pipeline_analytics(db: Session = Depends(get_db)):
    """Get deal pipeline analytics"""
    stages = ["prospect", "qualified", "negotiation", "closed_won", "closed_lost"]
    stage_data = {}
    
    for stage in stages:
        stage_deals = db.query(Deal).filter(Deal.deal_stage == stage).all()
        stage_data[stage] = {
            "count": len(stage_deals),
            "total_value": sum(d.deal_value for d in stage_deals)
        }
    
    return {
        "pipeline": stage_data,
        "timestamp": datetime.utcnow()
    }

@app.get("/analytics/activity")
def get_activity_analytics(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get activity analytics"""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    interactions = db.query(Interaction).filter(Interaction.created_at >= start_date).count()
    tasks = db.query(Task).filter(Task.created_at >= start_date).count()
    
    return {
        "days": days,
        "interactions": interactions,
        "tasks": tasks,
        "total_activity": interactions + tasks,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
