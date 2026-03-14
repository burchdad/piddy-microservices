"""
Subscription Management Service - SaaS subscriptions and entitlements
Port: 8000 (standard)
Host Port: 8110
"""
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_subscriptions")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String(200), unique=True)
    plan_slug = Column(String(100), unique=True)
    description = Column(Text)
    price = Column(Float)
    currency = Column(String(10), default="USD")
    billing_period = Column(String(50))  # monthly, yearly, quarterly
    trial_days = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    features = Column(Text, default="[]")  # JSON array
    max_users = Column(Integer)
    max_api_calls = Column(Integer)
    storage_gb = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    plan_id = Column(Integer, index=True)
    subscription_id = Column(String(200), unique=True)
    status = Column(String(50), default="active")  # active, trial, paused, cancelled, expired
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_end = Column(DateTime)
    cancel_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(String(200))
    auto_renew = Column(Boolean, default=True)
    payment_method_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_plan', 'user_id', 'plan_id'),
        Index('idx_status', 'status'),
    )

class Feature(Base):
    __tablename__ = "features"
    id = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String(200), unique=True)
    feature_slug = Column(String(100), unique=True)
    description = Column(Text)
    feature_type = Column(String(50))  # usage, limit, capability
    default_value = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

class PlanFeature(Base):
    __tablename__ = "plan_features"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, index=True)
    feature_id = Column(Integer, index=True)
    entitlement_value = Column(String(200))  # unlimited, number, true/false
    created_at = Column(DateTime, default=datetime.utcnow)

class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_subscription_metric', 'subscription_id', 'metric_name'),
    )

class BillingCycle(Base):
    __tablename__ = "billing_cycles"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, index=True)
    cycle_start = Column(DateTime)
    cycle_end = Column(DateTime)
    amount = Column(Float)
    status = Column(String(50), default="pending")  # pending, charged, failed, refunded
    invoice_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, index=True)
    event_type = Column(String(100))  # created, upgraded, downgraded, renewed, cancelled
    event_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class PlanCreate(BaseModel):
    plan_name: str
    plan_slug: str
    description: str = None
    price: float
    currency: str = "USD"
    billing_period: str
    trial_days: int = 0
    features: list = Field(default=None)
    max_users: int = None
    max_api_calls: int = None
    storage_gb: float = None

class SubscriptionCreate(BaseModel):
    user_id: str
    plan_id: int
    payment_method_id: int

class UpgradeRequest(BaseModel):
    subscription_id: int
    new_plan_id: int

class CancelRequest(BaseModel):
    subscription_id: int
    reason: str = None
    effective_immediately: bool = False

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Subscription Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    plans = db.query(SubscriptionPlan).count()
    active_subs = db.query(Subscription).filter(Subscription.status == "active").count()
    total_subs = db.query(Subscription).count()
    features = db.query(Feature).count()
    
    return {
        "total_plans": plans,
        "total_subscriptions": total_subs,
        "active_subscriptions": active_subs,
        "total_features": features,
        "timestamp": datetime.utcnow()
    }

# Plan Endpoints
@app.post("/plans")
def create_plan(plan: PlanCreate, db: Session = Depends(get_db)):
    """Create subscription plan"""
    db_plan = SubscriptionPlan(
        plan_name=plan.plan_name,
        plan_slug=plan.plan_slug,
        description=plan.description,
        price=plan.price,
        currency=plan.currency,
        billing_period=plan.billing_period,
        trial_days=plan.trial_days,
        features=json.dumps(plan.features) if plan.features else "[]",
        max_users=plan.max_users,
        max_api_calls=plan.max_api_calls,
        storage_gb=plan.storage_gb
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    return {
        "id": db_plan.id,
        "plan_name": db_plan.plan_name,
        "price": db_plan.price,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/plans")
def list_plans(active_only: bool = Query(True), db: Session = Depends(get_db)):
    """List subscription plans"""
    query = db.query(SubscriptionPlan)
    if active_only:
        query = query.filter(SubscriptionPlan.is_active == True)
    
    plans = query.all()
    
    return {
        "total": len(plans),
        "plans": plans,
        "timestamp": datetime.utcnow()
    }

@app.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get plan details"""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {
        "id": plan.id,
        "plan_name": plan.plan_name,
        "price": plan.price,
        "features": json.loads(plan.features),
        "timestamp": datetime.utcnow()
    }

# Subscription Endpoints
@app.post("/subscriptions")
def create_subscription(sub: SubscriptionCreate, db: Session = Depends(get_db)):
    """Create subscription for user"""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    trial_end = None
    if plan.trial_days > 0:
        trial_end = datetime.utcnow() + timedelta(days=plan.trial_days)
    
    db_sub = Subscription(
        user_id=sub.user_id,
        plan_id=sub.plan_id,
        subscription_id=f"sub_{datetime.utcnow().timestamp()}",
        status="trial" if trial_end else "active",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),
        trial_end=trial_end,
        payment_method_id=sub.payment_method_id
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    
    return {
        "id": db_sub.id,
        "user_id": sub.user_id,
        "plan_id": sub.plan_id,
        "status": db_sub.status,
        "created_at": db_sub.created_at,
        "timestamp": datetime.utcnow()
    }

@app.get("/subscriptions/{user_id}")
def get_user_subscription(user_id: str, db: Session = Depends(get_db)):
    """Get user's active subscription"""
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status.in_(["active", "trial"])
    ).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Active subscription not found")
    
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
    
    return {
        "id": sub.id,
        "plan": plan.plan_name if plan else None,
        "status": sub.status,
        "current_period_end": sub.current_period_end,
        "timestamp": datetime.utcnow()
    }

@app.post("/subscriptions/{subscription_id}/upgrade")
def upgrade_subscription(upgrade: UpgradeRequest, db: Session = Depends(get_db)):
    """Upgrade subscription to better plan"""
    sub = db.query(Subscription).filter(Subscription.id == upgrade.subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == upgrade.new_plan_id).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="New plan not found")
    
    sub.plan_id = upgrade.new_plan_id
    sub.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "subscription_id": subscription_id,
        "new_plan_id": upgrade.new_plan_id,
        "status": "upgraded",
        "timestamp": datetime.utcnow()
    }

@app.post("/subscriptions/{subscription_id}/cancel")
def cancel_subscription(subscription_id: int, cancel: CancelRequest, db: Session = Depends(get_db)):
    """Cancel subscription"""
    sub = db.query(Subscription).filter(Subscription.id == cancel.subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if cancel.effective_immediately:
        sub.status = "cancelled"
        sub.cancelled_at = datetime.utcnow()
    else:
        sub.cancel_at = sub.current_period_end
    
    sub.cancellation_reason = cancel.reason
    db.commit()
    
    return {
        "subscription_id": cancel.subscription_id,
        "status": sub.status,
        "cancelled_at": sub.cancelled_at,
        "timestamp": datetime.utcnow()
    }

# Feature Endpoints
@app.post("/features")
def create_feature(feature_name: str, feature_slug: str, feature_type: str, db: Session = Depends(get_db)):
    """Create feature"""
    db_feature = Feature(
        feature_name=feature_name,
        feature_slug=feature_slug,
        feature_type=feature_type
    )
    db.add(db_feature)
    db.commit()
    db.refresh(db_feature)
    
    return {
        "id": db_feature.id,
        "feature_name": db_feature.feature_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/subscriptions/{subscription_id}/entitlements")
def get_subscription_entitlements(subscription_id: int, db: Session = Depends(get_db)):
    """Get features entitlements for subscription"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    entitlements = db.query(PlanFeature).filter(PlanFeature.plan_id == sub.plan_id).all()
    
    return {
        "subscription_id": subscription_id,
        "entitlement_count": len(entitlements),
        "entitlements": entitlements,
        "timestamp": datetime.utcnow()
    }

# Usage Tracking
@app.post("/subscriptions/{subscription_id}/record-usage")
def record_usage(
    subscription_id: int,
    metric_name: str,
    metric_value: float,
    db: Session = Depends(get_db)
):
    """Record subscription usage"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    usage = UsageTracking(
        subscription_id=subscription_id,
        metric_name=metric_name,
        metric_value=metric_value,
        period_start=sub.current_period_start,
        period_end=sub.current_period_end
    )
    db.add(usage)
    db.commit()
    
    return {
        "subscription_id": subscription_id,
        "metric": metric_name,
        "value": metric_value,
        "status": "recorded",
        "timestamp": datetime.utcnow()
    }

@app.get("/subscriptions/{subscription_id}/usage")
def get_subscription_usage(subscription_id: int, db: Session = Depends(get_db)):
    """Get usage during current billing period"""
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    usage = db.query(UsageTracking).filter(
        UsageTracking.subscription_id == subscription_id
    ).all()
    
    return {
        "subscription_id": subscription_id,
        "period_start": sub.current_period_start,
        "period_end": sub.current_period_end,
        "usage_count": len(usage),
        "usage": usage,
        "timestamp": datetime.utcnow()
    }

# Billing Cycle Endpoints
@app.get("/subscriptions/{subscription_id}/billing-cycles")
def get_billing_cycles(subscription_id: int, db: Session = Depends(get_db)):
    """Get billing cycles for subscription"""
    cycles = db.query(BillingCycle).filter(
        BillingCycle.subscription_id == subscription_id
    ).order_by(BillingCycle.cycle_start.desc()).all()
    
    return {
        "subscription_id": subscription_id,
        "cycle_count": len(cycles),
        "cycles": cycles,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
