"""
File Storage Service - File uploads, S3-compatible storage, CDN
Port: 8000 (standard)
Host Port: 8114
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_storage")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class StorageBucket(Base):
    __tablename__ = "storage_buckets"
    id = Column(Integer, primary_key=True, index=True)
    bucket_name = Column(String(200), unique=True)
    bucket_type = Column(String(50))  # documents, images, videos, archives
    owner_id = Column(String(100), index=True)
    region = Column(String(100), default="us-east-1")
    is_public = Column(Boolean, default=False)
    max_size_gb = Column(Float)
    current_size_gb = Column(Float, default=0.0)
    file_count = Column(Integer, default=0)
    versioning_enabled = Column(Boolean, default=False)
    lifecycle_policy = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class StorageFile(Base):
    __tablename__ = "storage_files"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(100), unique=True)
    bucket_id = Column(Integer, index=True)
    filename = Column(String(500))
    file_key = Column(String(500))  # S3-like key path
    mime_type = Column(String(100))
    file_size = Column(Integer)  # bytes
    version = Column(Integer, default=1)
    storage_class = Column(String(50), default="STANDARD")  # STANDARD, INFREQUENT_ACCESS, GLACIER
    is_deleted = Column(Boolean, default=False)
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime)
    public_url = Column(String(500))
    cdn_url = Column(String(500))
    metadata = Column(Text, default="{}")
    virus_scanned = Column(Boolean, default=False)
    scan_result = Column(String(50))  # clean, infected, pending
    
    __table_args__ = (
        Index('idx_bucket_filename', 'bucket_id', 'filename'),
        Index('idx_file_key', 'file_key'),
    )

class FileVersion(Base):
    __tablename__ = "file_versions"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True)
    version_number = Column(Integer)
    file_size = Column(Integer)
    storage_class = Column(String(50))
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class StorageQuota(Base):
    __tablename__ = "storage_quotas"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(String(100), unique=True)
    quota_gb = Column(Float)
    used_gb = Column(Float, default=0.0)
    file_limit = Column(Integer)
    files_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DownloadLog(Base):
    __tablename__ = "download_logs"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True)
    downloader_ip = Column(String(45))
    downloader_id = Column(String(100))
    download_size = Column(Integer)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_file_timestamp', 'file_id', 'downloaded_at'),
    )

class StorageAnalytics(Base):
    __tablename__ = "storage_analytics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    bucket_id = Column(Integer, index=True)
    period = Column(String(50))  # hourly, daily, monthly
    recorded_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class BucketCreate(BaseModel):
    bucket_name: str
    bucket_type: str
    max_size_gb: float = 100.0
    is_public: bool = False

class FileUpload(BaseModel):
    filename: str
    file_key: str
    mime_type: str
    file_size: int
    storage_class: str = "STANDARD"

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="File Storage Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    buckets = db.query(StorageBucket).count()
    files = db.query(StorageFile).filter(StorageFile.is_deleted == False).count()
    total_size = db.query(StorageFile).with_entities(StorageFile.file_size).all()
    total_bytes = sum(f[0] for f in total_size)
    
    return {
        "total_buckets": buckets,
        "total_files": files,
        "total_size_gb": total_bytes / (1024 ** 3),
        "timestamp": datetime.utcnow()
    }

# Bucket Endpoints
@app.post("/buckets")
def create_bucket(bucket: BucketCreate, owner_id: str = Query(None), db: Session = Depends(get_db)):
    """Create storage bucket"""
    db_bucket = StorageBucket(
        bucket_name=bucket.bucket_name,
        bucket_type=bucket.bucket_type,
        owner_id=owner_id,
        max_size_gb=bucket.max_size_gb,
        is_public=bucket.is_public
    )
    db.add(db_bucket)
    
    # Create quota for owner
    quota = db.query(StorageQuota).filter(StorageQuota.owner_id == owner_id).first()
    if not quota:
        quota = StorageQuota(
            owner_id=owner_id,
            quota_gb=bucket.max_size_gb * 10
        )
        db.add(quota)
    
    db.commit()
    db.refresh(db_bucket)
    
    return {
        "id": db_bucket.id,
        "bucket_name": db_bucket.bucket_name,
        "status": "created",
        "max_size_gb": db_bucket.max_size_gb,
        "timestamp": datetime.utcnow()
    }

@app.get("/buckets")
def list_buckets(owner_id: str = Query(None), db: Session = Depends(get_db)):
    """List storage buckets"""
    query = db.query(StorageBucket)
    
    if owner_id:
        query = query.filter(StorageBucket.owner_id == owner_id)
    
    buckets = query.all()
    
    return {
        "total": len(buckets),
        "buckets": buckets,
        "timestamp": datetime.utcnow()
    }

@app.get("/buckets/{bucket_id}")
def get_bucket(bucket_id: int, db: Session = Depends(get_db)):
    """Get bucket details"""
    bucket = db.query(StorageBucket).filter(StorageBucket.id == bucket_id).first()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    file_count = db.query(StorageFile).filter(
        StorageFile.bucket_id == bucket_id,
        StorageFile.is_deleted == False
    ).count()
    
    return {
        "id": bucket.id,
        "bucket_name": bucket.bucket_name,
        "file_count": file_count,
        "current_size_gb": bucket.current_size_gb,
        "max_size_gb": bucket.max_size_gb,
        "timestamp": datetime.utcnow()
    }

# File Endpoints
@app.post("/buckets/{bucket_id}/files")
def upload_file(bucket_id: int, file: FileUpload, uploaded_by: str = Query(None), db: Session = Depends(get_db)):
    """Upload file to bucket"""
    bucket = db.query(StorageBucket).filter(StorageBucket.id == bucket_id).first()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    
    db_file = StorageFile(
        file_id=f"file_{datetime.utcnow().timestamp()}",
        bucket_id=bucket_id,
        filename=file.filename,
        file_key=file.file_key,
        mime_type=file.mime_type,
        file_size=file.file_size,
        storage_class=file.storage_class,
        uploaded_by=uploaded_by,
        public_url=f"https://{bucket.bucket_name}.s3.amazonaws.com/{file.file_key}"
    )
    db.add(db_file)
    bucket.current_size_gb += (file.file_size / (1024 ** 3))
    bucket.file_count += 1
    db.commit()
    db.refresh(db_file)
    
    return {
        "id": db_file.id,
        "file_id": db_file.file_id,
        "filename": db_file.filename,
        "public_url": db_file.public_url,
        "status": "uploaded",
        "timestamp": datetime.utcnow()
    }

@app.get("/buckets/{bucket_id}/files")
def list_bucket_files(
    bucket_id: int,
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List files in bucket"""
    files = db.query(StorageFile).filter(
        StorageFile.bucket_id == bucket_id,
        StorageFile.is_deleted == False
    ).order_by(StorageFile.uploaded_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "bucket_id": bucket_id,
        "file_count": len(files),
        "files": files,
        "timestamp": datetime.utcnow()
    }

@app.get("/files/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    """Get file details"""
    file = db.query(StorageFile).filter(StorageFile.id == file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(status_code=404, detail="File not found")
    
    file.accessed_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": file.id,
        "filename": file.filename,
        "file_size": file.file_size,
        "mime_type": file.mime_type,
        "public_url": file.public_url,
        "uploaded_at": file.uploaded_at,
        "timestamp": datetime.utcnow()
    }

@app.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """Delete file (soft delete)"""
    file = db.query(StorageFile).filter(StorageFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file.is_deleted = True
    bucket = db.query(StorageBucket).filter(StorageBucket.id == file.bucket_id).first()
    if bucket:
        bucket.current_size_gb -= (file.file_size / (1024 ** 3))
        bucket.file_count -= 1
    db.commit()
    
    return {
        "file_id": file_id,
        "status": "deleted",
        "timestamp": datetime.utcnow()
    }

# Download Tracking
@app.post("/files/{file_id}/download")
def track_download(file_id: int, downloader_ip: str = Query(None), db: Session = Depends(get_db)):
    """Track file download"""
    file = db.query(StorageFile).filter(StorageFile.id == file_id).first()
    if not file or file.is_deleted:
        raise HTTPException(status_code=404, detail="File not found")
    
    download_log = DownloadLog(
        file_id=file_id,
        downloader_ip=downloader_ip,
        download_size=file.file_size
    )
    db.add(download_log)
    db.commit()
    
    return {
        "file_id": file_id,
        "download_url": file.public_url,
        "timestamp": datetime.utcnow()
    }

# Version Control
@app.get("/files/{file_id}/versions")
def get_file_versions(file_id: int, db: Session = Depends(get_db)):
    """Get file version history"""
    versions = db.query(FileVersion).filter(FileVersion.file_id == file_id).all()
    
    return {
        "file_id": file_id,
        "version_count": len(versions),
        "versions": versions,
        "timestamp": datetime.utcnow()
    }

# Storage Analytics
@app.get("/analytics/usage")
def get_usage_analytics(owner_id: str = Query(None), db: Session = Depends(get_db)):
    """Get storage usage analytics"""
    if owner_id:
        quota = db.query(StorageQuota).filter(StorageQuota.owner_id == owner_id).first()
        if not quota:
            raise HTTPException(status_code=404, detail="Quota not found")
        
        return {
            "owner_id": owner_id,
            "quota_gb": quota.quota_gb,
            "used_gb": quota.used_gb,
            "available_gb": quota.quota_gb - quota.used_gb,
            "usage_percent": (quota.used_gb / quota.quota_gb * 100) if quota.quota_gb > 0 else 0,
            "timestamp": datetime.utcnow()
        }
    
    all_quotas = db.query(StorageQuota).all()
    total_quota = sum(q.quota_gb for q in all_quotas)
    total_used = sum(q.used_gb for q in all_quotas)
    
    return {
        "total_quota_gb": total_quota,
        "total_used_gb": total_used,
        "total_available_gb": total_quota - total_used,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
