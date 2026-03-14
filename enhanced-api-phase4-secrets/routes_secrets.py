"""
Secrets Management Service - FastAPI Routes

Encrypted secret storage, versioning, rotation, and access control.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query, Header
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean, JSON, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel, Field, SecretStr
from datetime import datetime, timedelta
import uuid
import logging
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Database
DATABASE_URL = os.getenv("DATABASE_URL_SECRETS", "postgresql://piddy:piddy_secure_pwd@localhost:5432/piddy_secrets")
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Encryption setup
ENCRYPTION_KEY = os.getenv("SECRETS_ENCRYPTION_KEY", Fernet.generate_key()).encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Secrets Management database initialized")

def encrypt_value(value: str) -> str:
    """Encrypt a secret value"""
    return cipher_suite.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a secret value"""
    return cipher_suite.decrypt(encrypted_value.encode()).decode()


# Models
class Secret(Base):
    __tablename__ = "secrets"
    __table_args__ = (
        Index('idx_secret_name', 'name'),
        Index('idx_secret_owner', 'owner_id'),
        Index('idx_secret_active', 'active'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    secret_type = Column(String(50), nullable=False)  # password, api_key, token, etc.
    
    # Encrypted value
    encrypted_value = Column(Text, nullable=False)
    
    # Metadata
    tags = Column(JSON)  # Tags for organization
    metadata = Column(JSON)
    
    # Lifecycle
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # Optional expiration
    
    # Audit
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)


class SecretVersion(Base):
    __tablename__ = "secret_versions"
    __table_args__ = (
        Index('idx_version_secret_id', 'secret_id'),
        Index('idx_version_created', 'created_at'),
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    secret_id = Column(PG_UUID(as_uuid=True), nullable=False)
    version = Column(Integer, nullable=False)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255))


class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    secret_id = Column(PG_UUID(as_uuid=True), nullable=False)
    accessed_by = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)  # read, update, delete
    ip_address = Column(String(50))
    granted = Column(Boolean, default=True)
    reason_denied = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)


# Schemas
class CreateSecretRequest(BaseModel):
    name: str
    secret_type: str
    value: SecretStr
    tags: Optional[list] = None
    metadata: Optional[dict] = None
    expires_at: Optional[datetime] = None


class SecretResponse(BaseModel):
    id: str
    name: str
    secret_type: str
    tags: Optional[list]
    created_at: datetime
    expires_at: Optional[datetime]


class AccessSecretRequest(BaseModel):
    secret_name: str


# FastAPI App
app = FastAPI(
    title="Piddy Secrets Management Service",
    description="Encrypted secret storage and lifecycle management",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    init_db()
    logger.info("Secrets Management Service started")


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.post("/secrets", response_model=SecretResponse)
def create_secret(req: CreateSecretRequest, owner_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """Create a new secret"""
    try:
        encrypted = encrypt_value(req.value.get_secret_value())
        
        secret = Secret(
            owner_id=owner_id,
            name=req.name,
            secret_type=req.secret_type,
            encrypted_value=encrypted,
            tags=req.tags,
            metadata=req.metadata,
            expires_at=req.expires_at,
        )
        
        # Create initial version
        version = SecretVersion(
            secret_id=secret.id,
            version=1,
            encrypted_value=encrypted,
            created_by=owner_id,
        )
        
        db.add(secret)
        db.add(version)
        db.commit()
        
        logger.info(f"Secret {secret.id} created by {owner_id}")
        
        return SecretResponse(
            id=str(secret.id),
            name=secret.name,
            secret_type=secret.secret_type,
            tags=secret.tags,
            created_at=secret.created_at,
            expires_at=secret.expires_at,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to create secret")


@app.get("/secrets/{secret_id}", response_model=dict)
def get_secret(secret_id: str, owner_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """Retrieve a secret (decrypted)"""
    secret = db.query(Secret).filter_by(id=secret_id, owner_id=owner_id, active=True).first()
    
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    if secret.expires_at and secret.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Secret has expired")
    
    try:
        decrypted = decrypt_value(secret.encrypted_value)
        secret.last_accessed = datetime.utcnow()
        secret.access_count += 1
        
        log = AccessLog(
            secret_id=secret.id,
            accessed_by=owner_id,
            action="read",
            granted=True,
        )
        db.add(log)
        db.commit()
        
        return {
            "id": str(secret.id),
            "name": secret.name,
            "secret_type": secret.secret_type,
            "value": decrypted,
            "created_at": secret.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to decrypt secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret")


@app.get("/secrets")
def list_secrets(owner_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """List all secrets for owner (metadata only, not values)"""
    secrets = db.query(Secret).filter_by(owner_id=owner_id, active=True).all()
    return {
        "secrets": [
            {
                "id": str(s.id),
                "name": s.name,
                "secret_type": s.secret_type,
                "tags": s.tags,
                "created_at": s.created_at.isoformat(),
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in secrets
        ]
    }


@app.post("/secrets/{secret_id}/rotate", response_model=dict)
def rotate_secret(secret_id: str, req: CreateSecretRequest, owner_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """Rotate a secret to a new value"""
    secret = db.query(Secret).filter_by(id=secret_id, owner_id=owner_id).first()
    
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    try:
        encrypted = encrypt_value(req.value.get_secret_value())
        
        latest_version = db.query(SecretVersion).filter_by(secret_id=secret.id).order_by(
            SecretVersion.version.desc()
        ).first()
        new_version_num = (latest_version.version if latest_version else 0) + 1
        
        version = SecretVersion(
            secret_id=secret.id,
            version=new_version_num,
            encrypted_value=encrypted,
            created_by=owner_id,
        )
        
        secret.encrypted_value = encrypted
        secret.updated_at = datetime.utcnow()
        
        db.add(version)
        db.commit()
        
        logger.info(f"Secret {secret_id} rotated to version {new_version_num}")
        
        return {"version": new_version_num, "rotated_at": datetime.utcnow().isoformat()}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to rotate secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate secret")


@app.delete("/secrets/{secret_id}")
def delete_secret(secret_id: str, owner_id: str = Query(...), db: SessionLocal = Depends(get_db)):
    """Soft-delete a secret (mark as inactive)"""
    secret = db.query(Secret).filter_by(id=secret_id, owner_id=owner_id).first()
    
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    secret.active = False
    db.commit()
    logger.info(f"Secret {secret_id} deleted by {owner_id}")
    
    return {"status": "deleted"}


@app.get("/metrics")
def metrics(db: SessionLocal = Depends(get_db)):
    """Get secrets management metrics"""
    total_secrets = db.query(Secret).count()
    active_secrets = db.query(Secret).filter_by(active=True).count()
    expired = db.query(Secret).filter(Secret.expires_at < datetime.utcnow()).count()
    total_accesses = db.query(AccessLog).count()
    
    return {
        "total_secrets": total_secrets,
        "active_secrets": active_secrets,
        "expired_secrets": expired,
        "total_accesses": total_accesses,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
