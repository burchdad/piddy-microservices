"""
Payment Processing Service - Stripe/PayPal integration and transactions
Port: 8000 (standard)
Host Port: 8109
"""
import os
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_payments")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    method_type = Column(String(50))  # credit_card, debit_card, paypal, bank_account
    provider = Column(String(50))  # stripe, paypal, etc
    provider_id = Column(String(200), unique=True)
    last_four = Column(String(4))
    expiry_month = Column(Integer)
    expiry_year = Column(Integer)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    payment_method_id = Column(Integer, index=True)
    transaction_id = Column(String(200), unique=True, index=True)
    provider = Column(String(50))  # stripe, paypal
    amount = Column(Float)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    transaction_type = Column(String(50))  # charge, refund, subscription_charge
    description = Column(Text)
    metadata = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    invoice_number = Column(String(50), unique=True)
    amount = Column(Float)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="draft")  # draft, sent, paid, overdue, cancelled
    items = Column(Text, default="[]")
    issued_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    notes = Column(Text)

class Refund(Base):
    __tablename__ = "refunds"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, index=True)
    refund_id = Column(String(200), unique=True)
    amount = Column(Float)
    reason = Column(String(200))
    status = Column(String(50), default="pending")  # pending, completed, failed
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    metadata = Column(Text, default="{}")

class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_configs"
    id = Column(Integer, primary_key=True, index=True)
    gateway_name = Column(String(100))  # stripe, paypal
    public_key = Column(String(500))
    secret_key = Column(String(500))
    webhook_secret = Column(String(500))
    is_active = Column(Boolean, default=True)
    config_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class PaymentWebhook(Base):
    __tablename__ = "payment_webhooks"
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(String(200), unique=True)
    gateway = Column(String(50))
    event_type = Column(String(100))
    event_data = Column(Text)
    processed = Column(Boolean, default=False)
    error = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class PaymentMethodCreate(BaseModel):
    user_id: str
    method_type: str
    provider: str
    provider_id: str
    last_four: str
    expiry_month: int = None
    expiry_year: int = None

class TransactionCreate(BaseModel):
    user_id: str
    payment_method_id: int
    amount: float
    currency: str = "USD"
    description: str = None
    metadata: dict = Field(default=None)

class InvoiceCreate(BaseModel):
    user_id: str
    amount: float
    currency: str = "USD"
    items: list = Field(default=None)
    due_date: datetime = None
    notes: str = None

class RefundRequest(BaseModel):
    transaction_id: int
    amount: float = None
    reason: str = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Payment Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    payment_methods = db.query(PaymentMethod).count()
    transactions = db.query(Transaction).count()
    total_revenue = db.query(Transaction).filter(Transaction.status == "completed").count()
    invoices = db.query(Invoice).count()
    
    return {
        "total_payment_methods": payment_methods,
        "total_transactions": transactions,
        "completed_transactions": total_revenue,
        "total_invoices": invoices,
        "timestamp": datetime.utcnow()
    }

# Payment Method Endpoints
@app.post("/payment-methods")
def add_payment_method(method: PaymentMethodCreate, db: Session = Depends(get_db)):
    """Add payment method"""
    db_method = PaymentMethod(
        user_id=method.user_id,
        method_type=method.method_type,
        provider=method.provider,
        provider_id=method.provider_id,
        last_four=method.last_four,
        expiry_month=method.expiry_month,
        expiry_year=method.expiry_year
    )
    db.add(db_method)
    db.commit()
    db.refresh(db_method)
    
    return {
        "id": db_method.id,
        "method_type": db_method.method_type,
        "last_four": db_method.last_four,
        "status": "added",
        "timestamp": datetime.utcnow()
    }

@app.get("/payment-methods/{user_id}")
def get_user_payment_methods(user_id: str, db: Session = Depends(get_db)):
    """Get user's payment methods"""
    methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == user_id,
        PaymentMethod.is_active == True
    ).all()
    
    return {
        "user_id": user_id,
        "count": len(methods),
        "methods": methods,
        "timestamp": datetime.utcnow()
    }

@app.delete("/payment-methods/{method_id}")
def delete_payment_method(method_id: int, db: Session = Depends(get_db)):
    """Delete payment method"""
    method = db.query(PaymentMethod).filter(PaymentMethod.id == method_id).first()
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    method.is_active = False
    db.commit()
    
    return {
        "method_id": method_id,
        "status": "deleted",
        "timestamp": datetime.utcnow()
    }

# Transaction Endpoints
@app.post("/transactions")
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Create payment transaction"""
    db_transaction = Transaction(
        user_id=transaction.user_id,
        payment_method_id=transaction.payment_method_id,
        amount=transaction.amount,
        currency=transaction.currency,
        description=transaction.description,
        metadata=json.dumps(transaction.metadata) if transaction.metadata else "{}",
        status="pending",
        transaction_id=f"txn_{datetime.utcnow().timestamp()}"
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    return {
        "transaction_id": db_transaction.id,
        "amount": db_transaction.amount,
        "status": "pending",
        "created_at": db_transaction.created_at,
        "timestamp": datetime.utcnow()
    }

@app.get("/transactions/{user_id}")
def get_user_transactions(
    user_id: str,
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get user transactions"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "user_id": user_id,
        "count": len(transactions),
        "transactions": transactions,
        "timestamp": datetime.utcnow()
    }

@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get transaction details"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "id": transaction.id,
        "amount": transaction.amount,
        "status": transaction.status,
        "created_at": transaction.created_at,
        "timestamp": datetime.utcnow()
    }

@app.post("/transactions/{transaction_id}/confirm")
def confirm_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Confirm/complete transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction.status = "completed"
    transaction.completed_at = datetime.utcnow()
    db.commit()
    
    return {
        "transaction_id": transaction_id,
        "status": "completed",
        "completed_at": transaction.completed_at,
        "timestamp": datetime.utcnow()
    }

# Invoice Endpoints
@app.post("/invoices")
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """Create invoice"""
    db_invoice = Invoice(
        user_id=invoice.user_id,
        invoice_number=f"INV-{datetime.utcnow().timestamp()}",
        amount=invoice.amount,
        currency=invoice.currency,
        items=json.dumps(invoice.items) if invoice.items else "[]",
        due_date=invoice.due_date,
        notes=invoice.notes
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    return {
        "id": db_invoice.id,
        "invoice_number": db_invoice.invoice_number,
        "amount": db_invoice.amount,
        "status": "draft",
        "timestamp": datetime.utcnow()
    }

@app.get("/invoices/{user_id}")
def get_user_invoices(user_id: str, db: Session = Depends(get_db)):
    """Get user invoices"""
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id).all()
    
    return {
        "user_id": user_id,
        "count": len(invoices),
        "invoices": invoices,
        "timestamp": datetime.utcnow()
    }

@app.post("/invoices/{invoice_id}/send")
def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Send invoice to user"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = "sent"
    db.commit()
    
    return {
        "invoice_id": invoice_id,
        "status": "sent",
        "timestamp": datetime.utcnow()
    }

# Refund Endpoints
@app.post("/refunds")
def create_refund(refund: RefundRequest, db: Session = Depends(get_db)):
    """Create refund"""
    transaction = db.query(Transaction).filter(Transaction.id == refund.transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    refund_amount = refund.amount or transaction.amount
    
    db_refund = Refund(
        transaction_id=refund.transaction_id,
        refund_id=f"ref_{datetime.utcnow().timestamp()}",
        amount=refund_amount,
        reason=refund.reason,
        status="pending"
    )
    db.add(db_refund)
    db.commit()
    db.refresh(db_refund)
    
    return {
        "id": db_refund.id,
        "refund_id": db_refund.refund_id,
        "amount": db_refund.amount,
        "status": "pending",
        "timestamp": datetime.utcnow()
    }

@app.get("/refunds/{user_id}")
def get_user_refunds(user_id: str, db: Session = Depends(get_db)):
    """Get user refunds"""
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    transaction_ids = [t.id for t in transactions]
    
    refunds = db.query(Refund).filter(Refund.transaction_id.in_(transaction_ids)).all()
    
    return {
        "user_id": user_id,
        "count": len(refunds),
        "refunds": refunds,
        "timestamp": datetime.utcnow()
    }

# Statistics Endpoints
@app.get("/stats/revenue")
def get_revenue_stats(days: int = Query(30, le=365), db: Session = Depends(get_db)):
    """Get revenue statistics"""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    completed_transactions = db.query(Transaction).filter(
        Transaction.status == "completed",
        Transaction.created_at >= start_date
    ).all()
    
    total_revenue = sum(t.amount for t in completed_transactions)
    
    return {
        "days": days,
        "total_revenue": total_revenue,
        "transaction_count": len(completed_transactions),
        "average_transaction": total_revenue / len(completed_transactions) if completed_transactions else 0,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
