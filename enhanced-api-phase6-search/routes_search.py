"""
Search Service - Full-text search, filtering, faceted search
Port: 8000 (standard)
Host Port: 8111
"""
import os
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, Index, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_search")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class SearchIndex(Base):
    __tablename__ = "search_indices"
    id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String(200), unique=True)
    index_type = Column(String(100))  # documents, products, users, articles
    fields = Column(Text, default="[]")  # JSON array of searchable fields
    is_active = Column(Integer, default=1)
    last_indexed = Column(DateTime)
    document_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SearchDocument(Base):
    __tablename__ = "search_documents"
    id = Column(Integer, primary_key=True, index=True)
    index_id = Column(Integer, index=True)
    document_id = Column(String(200), index=True)
    title = Column(String(500))
    content = Column(Text)
    keywords = Column(Text, default="[]")
    metadata = Column(Text, default="{}")
    rank_score = Column(Float, default=0.0)
    indexed_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)
    
    __table_args__ = (
        Index('idx_index_active', 'index_id', 'is_active'),
    )

class SearchQuery(Base):
    __tablename__ = "search_queries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    query_text = Column(String(500))
    index_searched = Column(String(200))
    results_count = Column(Integer, default=0)
    execution_time_ms = Column(Float)
    filters_applied = Column(Text, default="{}")
    clicked_result = Column(Integer)  # document ID if clicked
    clicked_rank = Column(Integer)
    searched_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'searched_at'),
    )

class SearchFacet(Base):
    __tablename__ = "search_facets"
    id = Column(Integer, primary_key=True, index=True)
    index_id = Column(Integer, index=True)
    facet_name = Column(String(200))
    facet_type = Column(String(100))  # category, tags, date_range, price_range
    facet_values = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)

class SearchFilter(Base):
    __tablename__ = "search_filters"
    id = Column(Integer, primary_key=True, index=True)
    index_id = Column(Integer, index=True)
    filter_name = Column(String(200))
    filter_type = Column(String(100))  # range, keyword, date, numeric
    filter_config = Column(Text, default="{}")
    applied_count = Column(Integer, default=0)
    last_applied = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class SearchAnalytics(Base):
    __tablename__ = "search_analytics"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200))
    metric_value = Column(Float)
    index_name = Column(String(200), index=True)
    period = Column(String(50))  # hourly, daily, weekly
    recorded_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class IndexCreate(BaseModel):
    index_name: str
    index_type: str
    fields: list = Field(default=None)

class DocumentIndex(BaseModel):
    document_id: str
    title: str
    content: str
    keywords: list = Field(default=None)
    metadata: dict = Field(default=None)

class SearchQueryRequest(BaseModel):
    index_name: str
    query: str
    filters: dict = Field(default=None)
    limit: int = 10
    offset: int = 0

class FacetRequest(BaseModel):
    index_id: int
    facet_name: str
    facet_type: str
    facet_values: list

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Search Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    indices = db.query(SearchIndex).count()
    documents = db.query(SearchDocument).count()
    queries = db.query(SearchQuery).count()
    
    return {
        "total_indices": indices,
        "total_documents": documents,
        "total_queries": queries,
        "timestamp": datetime.utcnow()
    }

# Index Management Endpoints
@app.post("/indices")
def create_index(index: IndexCreate, db: Session = Depends(get_db)):
    """Create search index"""
    db_index = SearchIndex(
        index_name=index.index_name,
        index_type=index.index_type,
        fields=json.dumps(index.fields) if index.fields else "[]"
    )
    db.add(db_index)
    db.commit()
    db.refresh(db_index)
    
    return {
        "id": db_index.id,
        "index_name": db_index.index_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/indices")
def list_indices(db: Session = Depends(get_db)):
    """List all search indices"""
    indices = db.query(SearchIndex).all()
    
    return {
        "total": len(indices),
        "indices": indices,
        "timestamp": datetime.utcnow()
    }

@app.get("/indices/{index_id}")
def get_index(index_id: int, db: Session = Depends(get_db)):
    """Get index details"""
    index = db.query(SearchIndex).filter(SearchIndex.id == index_id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    doc_count = db.query(SearchDocument).filter(SearchDocument.index_id == index_id).count()
    
    return {
        "id": index.id,
        "index_name": index.index_name,
        "document_count": doc_count,
        "last_indexed": index.last_indexed,
        "timestamp": datetime.utcnow()
    }

# Document Indexing Endpoints
@app.post("/indices/{index_id}/documents")
def index_document(index_id: int, doc: DocumentIndex, db: Session = Depends(get_db)):
    """Index a document"""
    index = db.query(SearchIndex).filter(SearchIndex.id == index_id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    db_doc = SearchDocument(
        index_id=index_id,
        document_id=doc.document_id,
        title=doc.title,
        content=doc.content,
        keywords=json.dumps(doc.keywords) if doc.keywords else "[]",
        metadata=json.dumps(doc.metadata) if doc.metadata else "{}"
    )
    db.add(db_doc)
    index.document_count = db.query(SearchDocument).filter(SearchDocument.index_id == index_id).count() + 1
    index.last_indexed = datetime.utcnow()
    db.commit()
    db.refresh(db_doc)
    
    return {
        "id": db_doc.id,
        "document_id": doc.document_id,
        "status": "indexed",
        "timestamp": datetime.utcnow()
    }

@app.post("/indices/{index_id}/documents/batch")
def batch_index_documents(index_id: int, docs: list[DocumentIndex], db: Session = Depends(get_db)):
    """Batch index documents"""
    index = db.query(SearchIndex).filter(SearchIndex.id == index_id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    db_docs = [
        SearchDocument(
            index_id=index_id,
            document_id=doc.document_id,
            title=doc.title,
            content=doc.content,
            keywords=json.dumps(doc.keywords) if doc.keywords else "[]",
            metadata=json.dumps(doc.metadata) if doc.metadata else "{}"
        )
        for doc in docs
    ]
    db.add_all(db_docs)
    index.last_indexed = datetime.utcnow()
    db.commit()
    
    return {
        "indexed": len(db_docs),
        "index_id": index_id,
        "status": "batch_indexed",
        "timestamp": datetime.utcnow()
    }

# Search Endpoints
@app.post("/search")
def search(search_req: SearchQueryRequest, user_id: str = Query(None), db: Session = Depends(get_db)):
    """Execute full-text search"""
    index = db.query(SearchIndex).filter(SearchIndex.index_name == search_req.index_name).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    # Simulate full-text search with LIKE (in production use Elasticsearch or similar)
    query = db.query(SearchDocument).filter(
        SearchDocument.index_id == index.id,
        SearchDocument.is_active == 1,
        (SearchDocument.title.ilike(f"%{search_req.query}%")) |
        (SearchDocument.content.ilike(f"%{search_req.query}%"))
    )
    
    # Apply filters
    if search_req.filters:
        for filter_key, filter_val in search_req.filters.items():
            if filter_key == "keyword":
                query = query.filter(SearchDocument.keywords.contains(filter_val))
    
    total_count = query.count()
    results = query.offset(search_req.offset).limit(search_req.limit).all()
    
    # Log search query
    search_log = SearchQuery(
        user_id=user_id,
        query_text=search_req.query,
        index_searched=search_req.index_name,
        results_count=total_count,
        filters_applied=json.dumps(search_req.filters) if search_req.filters else "{}"
    )
    db.add(search_log)
    db.commit()
    
    return {
        "query": search_req.query,
        "total_results": total_count,
        "results_returned": len(results),
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "document_id": r.document_id,
                "rank_score": r.rank_score
            }
            for r in results
        ],
        "timestamp": datetime.utcnow()
    }

@app.get("/search/suggestions")
def get_search_suggestions(
    query: str,
    index_name: str,
    limit: int = Query(5, le=20),
    db: Session = Depends(get_db)
):
    """Get search suggestions/autocomplete"""
    index = db.query(SearchIndex).filter(SearchIndex.index_name == index_name).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    suggestions = db.query(SearchDocument.title).filter(
        SearchDocument.index_id == index.id,
        SearchDocument.title.ilike(f"{query}%")
    ).distinct().limit(limit).all()
    
    return {
        "query": query,
        "suggestions": [s[0] for s in suggestions],
        "timestamp": datetime.utcnow()
    }

# Faceted Search Endpoints
@app.post("/indices/{index_id}/facets")
def create_facet(index_id: int, facet: FacetRequest, db: Session = Depends(get_db)):
    """Create facet for search"""
    index = db.query(SearchIndex).filter(SearchIndex.id == index_id).first()
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    
    db_facet = SearchFacet(
        index_id=index_id,
        facet_name=facet.facet_name,
        facet_type=facet.facet_type,
        facet_values=json.dumps(facet.facet_values)
    )
    db.add(db_facet)
    db.commit()
    
    return {
        "id": db_facet.id,
        "facet_name": db_facet.facet_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/indices/{index_id}/facets")
def get_facets(index_id: int, db: Session = Depends(get_db)):
    """Get available facets for index"""
    facets = db.query(SearchFacet).filter(SearchFacet.index_id == index_id).all()
    
    return {
        "index_id": index_id,
        "facet_count": len(facets),
        "facets": facets,
        "timestamp": datetime.utcnow()
    }

# Analytics Endpoints
@app.get("/analytics/popular-queries")
def get_popular_queries(days: int = Query(7, le=90), db: Session = Depends(get_db)):
    """Get popular search queries"""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    popular = db.query(
        SearchQuery.query_text,
        func.count(SearchQuery.id).label("count")
    ).filter(
        SearchQuery.searched_at >= start_date
    ).group_by(SearchQuery.query_text).order_by(func.count(SearchQuery.id).desc()).limit(20).all()
    
    return {
        "days": days,
        "popular_queries": [
            {"query": q[0], "count": q[1]} for q in popular
        ],
        "timestamp": datetime.utcnow()
    }

@app.get("/analytics/ctr")
def get_click_through_rate(db: Session = Depends(get_db)):
    """Get click-through rate metrics"""
    total_queries = db.query(SearchQuery).count()
    clicked_queries = db.query(SearchQuery).filter(SearchQuery.clicked_result.isnot(None)).count()
    
    ctr = (clicked_queries / total_queries * 100) if total_queries > 0 else 0
    
    return {
        "total_queries": total_queries,
        "clicked_queries": clicked_queries,
        "ctr_percentage": ctr,
        "timestamp": datetime.utcnow()
    }

@app.get("/analytics/query-logs")
def get_query_logs(
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get search query logs"""
    logs = db.query(SearchQuery).order_by(SearchQuery.searched_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total_logs": len(logs),
        "logs": logs,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
