"""
Content Management Service - CMS, articles, pages, media management
Port: 8000 (standard)
Host Port: 8113
"""
import os
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_cms")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Content(Base):
    __tablename__ = "content"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(String(100), unique=True)
    title = Column(String(500))
    slug = Column(String(500), unique=True)
    content_type = Column(String(50))  # post, page, article, blog
    content_body = Column(Text)
    excerpt = Column(Text)
    featured_image = Column(String(500))
    status = Column(String(50), default="draft")  # draft, published, archived, scheduled
    author_id = Column(String(100))
    category = Column(String(200))
    tags = Column(Text, default="[]")
    seo_metadata = Column(Text, default="{}")
    view_count = Column(Integer, default=0)
    published_at = Column(DateTime)
    scheduled_for = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)
    
    __table_args__ = (
        Index('idx_slug_status', 'slug', 'status'),
        Index('idx_category_status', 'category', 'status'),
    )

class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(100), unique=True)
    filename = Column(String(500))
    file_type = Column(String(50))  # image, video, document, audio
    mime_type = Column(String(100))
    file_size = Column(Integer)  # bytes
    url = Column(String(500))
    alt_text = Column(String(500))
    metadata = Column(Text, default="{}")
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=True)

class ContentVersion(Base):
    __tablename__ = "content_versions"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, index=True)
    version_number = Column(Integer)
    title = Column(String(500))
    content_body = Column(Text)
    changed_by = Column(String(100))
    change_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(200))
    template_slug = Column(String(200), unique=True)
    template_type = Column(String(100))  # blog, landing, page, email
    content_template = Column(Text)
    fields = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ContentSchedule(Base):
    __tablename__ = "content_schedules"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, index=True)
    scheduled_for = Column(DateTime, index=True)
    action = Column(String(50))  # publish, unpublish, auto_archive
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentComment(Base):
    __tablename__ = "content_comments"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, index=True)
    author_name = Column(String(200))
    author_email = Column(String(200))
    comment_text = Column(Text)
    status = Column(String(50), default="pending")  # pending, approved, spam, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class ContentCreate(BaseModel):
    title: str
    content_type: str
    content_body: str
    excerpt: str = None
    featured_image: str = None
    category: str = None
    tags: list = Field(default=None)
    seo_metadata: dict = Field(default=None)

class MediaUpload(BaseModel):
    filename: str
    file_type: str
    mime_type: str
    file_size: int
    url: str
    alt_text: str = None

class TemplateCreate(BaseModel):
    template_name: str
    template_slug: str
    template_type: str
    content_template: str
    fields: list = Field(default=None)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Content Management Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    content_count = db.query(Content).count()
    published_count = db.query(Content).filter(Content.status == "published").count()
    media_count = db.query(MediaAsset).count()
    
    return {
        "total_content": content_count,
        "published_content": published_count,
        "total_media": media_count,
        "timestamp": datetime.utcnow()
    }

# Content Endpoints
@app.post("/content")
def create_content(content: ContentCreate, author_id: str = Query(None), db: Session = Depends(get_db)):
    """Create content"""
    slug = content.title.lower().replace(" ", "-")
    
    db_content = Content(
        content_id=f"con_{datetime.utcnow().timestamp()}",
        title=content.title,
        slug=slug,
        content_type=content.content_type,
        content_body=content.content_body,
        excerpt=content.excerpt,
        featured_image=content.featured_image,
        category=content.category,
        tags=json.dumps(content.tags) if content.tags else "[]",
        seo_metadata=json.dumps(content.seo_metadata) if content.seo_metadata else "{}",
        author_id=author_id
    )
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    
    return {
        "id": db_content.id,
        "content_id": db_content.content_id,
        "title": db_content.title,
        "slug": db_content.slug,
        "status": "draft",
        "timestamp": datetime.utcnow()
    }

@app.get("/content")
def list_content(
    content_type: str = Query(None),
    status: str = Query("published"),
    category: str = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List content"""
    query = db.query(Content).filter(Content.status == status)
    
    if content_type:
        query = query.filter(Content.content_type == content_type)
    if category:
        query = query.filter(Content.category == category)
    
    content_list = query.order_by(Content.published_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": query.count(),
        "content": content_list,
        "timestamp": datetime.utcnow()
    }

@app.get("/content/{slug}")
def get_content_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get content by slug"""
    content = db.query(Content).filter(
        Content.slug == slug,
        Content.status == "published"
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Increment view count
    content.view_count += 1
    db.commit()
    
    return {
        "id": content.id,
        "title": content.title,
        "content_body": content.content_body,
        "author_id": content.author_id,
        "views": content.view_count,
        "published_at": content.published_at,
        "timestamp": datetime.utcnow()
    }

@app.put("/content/{content_id}")
def update_content(content_id: int, content_data: ContentCreate, db: Session = Depends(get_db)):
    """Update content"""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Create version before update
    version = ContentVersion(
        content_id=content_id,
        version_number=content.version,
        title=content.title,
        content_body=content.content_body
    )
    db.add(version)
    
    content.title = content_data.title
    content.content_body = content_data.content_body
    content.excerpt = content_data.excerpt
    content.category = content_data.category
    content.version += 1
    content.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": content.id,
        "version": content.version,
        "status": "updated",
        "timestamp": datetime.utcnow()
    }

@app.post("/content/{content_id}/publish")
def publish_content(content_id: int, db: Session = Depends(get_db)):
    """Publish content"""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content.status = "published"
    content.published_at = datetime.utcnow()
    db.commit()
    
    return {
        "id": content.id,
        "status": "published",
        "published_at": content.published_at,
        "timestamp": datetime.utcnow()
    }

# Media Endpoints
@app.post("/media")
def upload_media(media: MediaUpload, uploaded_by: str = Query(None), db: Session = Depends(get_db)):
    """Upload media asset"""
    db_media = MediaAsset(
        asset_id=f"med_{datetime.utcnow().timestamp()}",
        filename=media.filename,
        file_type=media.file_type,
        mime_type=media.mime_type,
        file_size=media.file_size,
        url=media.url,
        alt_text=media.alt_text,
        uploaded_by=uploaded_by
    )
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    
    return {
        "id": db_media.id,
        "asset_id": db_media.asset_id,
        "url": db_media.url,
        "status": "uploaded",
        "timestamp": datetime.utcnow()
    }

@app.get("/media")
def list_media(file_type: str = Query(None), db: Session = Depends(get_db)):
    """List media assets"""
    query = db.query(MediaAsset).filter(MediaAsset.is_public == True)
    
    if file_type:
        query = query.filter(MediaAsset.file_type == file_type)
    
    media_list = query.order_by(MediaAsset.uploaded_at.desc()).all()
    
    return {
        "total": len(media_list),
        "media": media_list,
        "timestamp": datetime.utcnow()
    }

# Template Endpoints
@app.post("/templates")
def create_template(template: TemplateCreate, db: Session = Depends(get_db)):
    """Create content template"""
    db_template = Template(
        template_name=template.template_name,
        template_slug=template.template_slug,
        template_type=template.template_type,
        content_template=template.content_template,
        fields=json.dumps(template.fields) if template.fields else "[]"
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    return {
        "id": db_template.id,
        "template_name": db_template.template_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/templates")
def list_templates(template_type: str = Query(None), db: Session = Depends(get_db)):
    """List templates"""
    query = db.query(Template)
    
    if template_type:
        query = query.filter(Template.template_type == template_type)
    
    templates = query.all()
    
    return {
        "total": len(templates),
        "templates": templates,
        "timestamp": datetime.utcnow()
    }

# Version Control Endpoints
@app.get("/content/{content_id}/versions")
def get_content_versions(content_id: int, db: Session = Depends(get_db)):
    """Get version history"""
    versions = db.query(ContentVersion).filter(
        ContentVersion.content_id == content_id
    ).order_by(ContentVersion.created_at.desc()).all()
    
    return {
        "content_id": content_id,
        "version_count": len(versions),
        "versions": versions,
        "timestamp": datetime.utcnow()
    }

# Comment Endpoints
@app.post("/content/{content_id}/comments")
def add_comment(content_id: int, author_name: str, author_email: str, comment_text: str, db: Session = Depends(get_db)):
    """Add comment to content"""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    db_comment = ContentComment(
        content_id=content_id,
        author_name=author_name,
        author_email=author_email,
        comment_text=comment_text
    )
    db.add(db_comment)
    db.commit()
    
    return {
        "id": db_comment.id,
        "status": "comment_added",
        "timestamp": datetime.utcnow()
    }

@app.get("/content/{content_id}/comments")
def get_comments(content_id: int, db: Session = Depends(get_db)):
    """Get approved comments for content"""
    comments = db.query(ContentComment).filter(
        ContentComment.content_id == content_id,
        ContentComment.status == "approved"
    ).all()
    
    return {
        "content_id": content_id,
        "comment_count": len(comments),
        "comments": comments,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
