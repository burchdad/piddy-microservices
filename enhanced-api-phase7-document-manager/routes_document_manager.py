"""
Document Manager Service - Document storage, versioning, OCR, full-text retrieval
Port: 8000 (standard)
Host Port: 8117
"""

import os
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/piddy_document_manager")
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    owner_id = Column(Integer, index=True)
    file_path = Column(String)
    mime_type = Column(String)
    file_size = Column(Integer)
    status = Column(String, default="active")  # active, archived, deleted
    versions = relationship("DocumentVersion", back_populates="document")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentVersion(Base):
    __tablename__ = "document_version"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document.id'))
    version_number = Column(Integer)
    file_path = Column(String)
    file_size = Column(Integer)
    changed_by = Column(Integer)
    change_summary = Column(String)
    document = relationship("Document", back_populates="versions")
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentOCR(Base):
    __tablename__ = "document_ocr"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document.id'), index=True)
    extracted_text = Column(Text)
    confidence_score = Column(Float)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentTag(Base):
    __tablename__ = "document_tag"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document.id'), index=True)
    tag = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentAccess(Base):
    __tablename__ = "document_access"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document.id'), index=True)
    user_id = Column(Integer, index=True)
    access_level = Column(String)  # read, write, admin
    shared_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class DocumentCreate(BaseModel):
    title: str
    owner_id: int

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class OCRRequest(BaseModel):
    language: str = "en"

class DocumentResponse(BaseModel):
    id: int
    title: str
    owner_id: int
    file_size: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# FastAPI App
app = FastAPI(title="Document Manager Service", version="1.0.0")

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
        "service": "document-manager",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(doc: DocumentCreate, db=Depends(get_db)):
    """Create new document metadata"""
    db_doc = Document(**doc.dict())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.get("/documents/{document_id}")
async def get_document(document_id: int, db=Depends(get_db)):
    """Get document metadata"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@app.put("/documents/{document_id}")
async def update_document(document_id: int, doc_update: DocumentUpdate, db=Depends(get_db)):
    """Update document metadata"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    for key, value in doc_update.dict(exclude_unset=True).items():
        setattr(doc, key, value)
    
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return doc

@app.post("/documents/{document_id}/upload")
async def upload_document(
    document_id: int,
    file: UploadFile = File(...),
    changed_by: int = None,
    change_summary: str = "",
    db=Depends(get_db)
):
    """Upload/replace document file"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get current version count
    version_count = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).count()
    
    # Create version record
    version = DocumentVersion(
        document_id=document_id,
        version_number=version_count + 1,
        file_path=f"documents/{document_id}/v{version_count + 1}/{file.filename}",
        file_size=file.size or 0,
        changed_by=changed_by or doc.owner_id,
        change_summary=change_summary
    )
    db.add(version)
    db.commit()
    
    return {
        "document_id": document_id,
        "version": version.version_number,
        "file": file.filename,
        "uploaded_at": datetime.utcnow()
    }

@app.get("/documents/{document_id}/versions")
async def get_document_versions(document_id: int, db=Depends(get_db)):
    """Get all versions of document"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).all()
    
    return [
        {
            "version": v.version_number,
            "file_path": v.file_path,
            "file_size": v.file_size,
            "changed_by": v.changed_by,
            "change_summary": v.change_summary,
            "created_at": v.created_at
        }
        for v in versions
    ]

@app.post("/documents/{document_id}/revert-version/{version_number}")
async def revert_to_version(
    document_id: int,
    version_number: int,
    db=Depends(get_db)
):
    """Revert document to specific version"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == version_number
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Create new version from old
    new_version = DocumentVersion(
        document_id=document_id,
        version_number=db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).count() + 1,
        file_path=version.file_path,
        file_size=version.file_size,
        changed_by=doc.owner_id,
        change_summary=f"Reverted to version {version_number}"
    )
    db.add(new_version)
    db.commit()
    
    return {"status": "reverted", "new_version": new_version.version_number}

@app.post("/documents/{document_id}/ocr")
async def extract_text_ocr(
    document_id: int,
    ocr_req: OCRRequest,
    db=Depends(get_db)
):
    """Extract text from document using OCR"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Simulated OCR extraction
    ocr = DocumentOCR(
        document_id=document_id,
        extracted_text="[OCR extracted text would go here - simulated]",
        confidence_score=0.92,
        language=ocr_req.language
    )
    db.add(ocr)
    db.commit()
    
    return {
        "document_id": document_id,
        "status": "ocr_complete",
        "confidence": 0.92,
        "language": ocr_req.language
    }

@app.get("/documents/{document_id}/text")
async def get_extracted_text(document_id: int, db=Depends(get_db)):
    """Get OCR extracted text"""
    ocr = db.query(DocumentOCR).filter(
        DocumentOCR.document_id == document_id
    ).order_by(DocumentOCR.created_at.desc()).first()
    
    if not ocr:
        raise HTTPException(status_code=404, detail="No OCR data found")
    
    return {
        "document_id": document_id,
        "text": ocr.extracted_text,
        "confidence": ocr.confidence_score,
        "language": ocr.language,
        "extracted_at": ocr.created_at
    }

@app.post("/documents/{document_id}/tag")
async def add_tag(document_id: int, tag: str, db=Depends(get_db)):
    """Add tag to document"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db_tag = DocumentTag(document_id=document_id, tag=tag)
    db.add(db_tag)
    db.commit()
    
    return {"document_id": document_id, "tag": tag, "added_at": datetime.utcnow()}

@app.get("/documents/search/{query}")
async def search_documents(query: str, db=Depends(get_db)):
    """Search documents by title or tags"""
    docs = db.query(Document).filter(
        Document.title.ilike(f"%{query}%")
    ).limit(20).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "owner_id": doc.owner_id,
            "created_at": doc.created_at
        }
        for doc in docs
    ]

@app.post("/documents/{document_id}/share")
async def share_document(document_id: int, user_id: int, access_level: str = "read", db=Depends(get_db)):
    """Share document with user"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if access_level not in ["read", "write", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid access level")
    
    access = DocumentAccess(
        document_id=document_id,
        user_id=user_id,
        access_level=access_level
    )
    db.add(access)
    db.commit()
    
    return {"document_id": document_id, "shared_with": user_id, "access": access_level}

@app.get("/metrics")
async def get_service_metrics(db=Depends(get_db)):
    """Get service metrics"""
    doc_count = db.query(Document).count()
    version_count = db.query(DocumentVersion).count()
    ocr_count = db.query(DocumentOCR).count()
    total_size = db.query(
        db.func.sum(Document.file_size)
    ).scalar() or 0
    
    return {
        "documents": doc_count,
        "versions": version_count,
        "ocr_extractions": ocr_count,
        "total_storage_bytes": total_size,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
