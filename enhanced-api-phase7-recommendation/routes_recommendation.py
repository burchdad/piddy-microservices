"""
Recommendation Engine Service - Collaborative filtering, personalized recommendations
Port: 8000 (standard)
Host Port: 8116
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/piddy_recommendation")
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association table for user preferences
user_item_association = Table(
    'user_item_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('item_id', Integer, ForeignKey('item.id')),
    Column('rating', Float),
    Column('interaction_count', Integer, default=1)
)

# SQLAlchemy Models
class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    preferences = relationship("Item", secondary=user_item_association, back_populates="users")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Item(Base):
    __tablename__ = "item"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    title = Column(String)
    category = Column(String, index=True)
    metadata = Column(String)  # JSON string
    popularity_score = Column(Float, default=0.0)
    users = relationship("User", secondary=user_item_association, back_populates="preferences")
    created_at = Column(DateTime, default=datetime.utcnow)

class Recommendation(Base):
    __tablename__ = "recommendation"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), index=True)
    item_id = Column(Integer, ForeignKey('item.id'), index=True)
    score = Column(Float)
    reason = Column(String)  # why recommended
    algorithm = Column(String)  # collaborative, content-based, hybrid
    clicked = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CollabFilter(Base):
    __tablename__ = "collab_filter"
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey('user.id'))
    user2_id = Column(Integer, ForeignKey('user.id'))
    similarity_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class UserCreate(BaseModel):
    external_id: str
    name: str
    email: str

class ItemCreate(BaseModel):
    external_id: str
    title: str
    category: str
    metadata: dict = {}

class RatingInput(BaseModel):
    user_id: int
    item_id: int
    rating: float = Field(..., ge=0.0, le=5.0)

class RecommendationResponse(BaseModel):
    item_id: int
    title: str
    score: float
    reason: str
    algorithm: str

    class Config:
        from_attributes = True

# FastAPI App
app = FastAPI(title="Recommendation Engine", version="1.0.0")

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
        "service": "recommendation-engine",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db=Depends(get_db)):
    """Create new user"""
    if db.query(User).filter(User.external_id == user.external_id).first():
        raise HTTPException(status_code=400, detail="User already exists")
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db=Depends(get_db)):
    """Create new item to recommend"""
    if db.query(Item).filter(Item.external_id == item.external_id).first():
        raise HTTPException(status_code=400, detail="Item already exists")
    db_item = Item(
        external_id=item.external_id,
        title=item.title,
        category=item.category,
        metadata=json.dumps(item.metadata)
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.post("/rate")
async def rate_item(rating: RatingInput, db=Depends(get_db)):
    """Record user rating/interaction with item"""
    user = db.query(User).filter(User.id == rating.user_id).first()
    item = db.query(Item).filter(Item.id == rating.item_id).first()
    
    if not user or not item:
        raise HTTPException(status_code=404, detail="User or item not found")
    
    # Update popularity score
    item.popularity_score += rating.rating * 0.1
    
    # Record recommendation if clicked
    rec = Recommendation(
        user_id=rating.user_id,
        item_id=rating.item_id,
        score=rating.rating,
        reason="direct_rating",
        algorithm="user_input",
        clicked=1
    )
    db.add(rec)
    db.commit()
    return {"status": "rated", "rating": rating.rating}

@app.get("/recommend/{user_id}")
async def get_recommendations(user_id: int, limit: int = 10, db=Depends(get_db)):
    """Get personalized recommendations for user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Collaborative filtering: find similar users
    similar_users = db.query(CollabFilter).filter(
        CollabFilter.user1_id == user_id
    ).order_by(CollabFilter.similarity_score.desc()).limit(5).all()
    
    similar_user_ids = [sf.user2_id for sf in similar_users]
    
    # Get items liked by similar users
    if similar_user_ids:
        recommendations = []
        for similar_user_id in similar_user_ids:
            items = db.query(Item).join(
                user_item_association,
                Item.id == user_item_association.c.item_id
            ).filter(
                user_item_association.c.user_id == similar_user_id
            ).limit(limit).all()
            
            for item in items:
                score = 4.5 + (0.1 * len(similar_user_ids))
                rec = Recommendation(
                    user_id=user_id,
                    item_id=item.id,
                    score=score,
                    reason=f"users_like_you_liked_this",
                    algorithm="collaborative_filtering"
                )
                db.add(rec)
                recommendations.append({
                    "item_id": item.id,
                    "title": item.title,
                    "score": score,
                    "reason": "collaborative_filtering"
                })
        
        db.commit()
        return recommendations[:limit]
    
    # Fallback: popular items
    popular_items = db.query(Item).order_by(Item.popularity_score.desc()).limit(limit).all()
    return [
        {
            "item_id": item.id,
            "title": item.title,
            "score": item.popularity_score,
            "reason": "trending"
        }
        for item in popular_items
    ]

@app.post("/calculate-similarity")
async def calculate_user_similarity(user1_id: int, user2_id: int, db=Depends(get_db)):
    """Calculate similarity between two users for collaborative filtering"""
    user1 = db.query(User).filter(User.id == user1_id).first()
    user2 = db.query(User).filter(User.id == user2_id).first()
    
    if not user1 or not user2:
        raise HTTPException(status_code=404, detail="Users not found")
    
    # Simple similarity: common rated items
    common_items = len(set([item.id for item in user1.preferences]) & 
                      set([item.id for item in user2.preferences]))
    total_items = len(set([item.id for item in user1.preferences]) | 
                     set([item.id for item in user2.preferences]))
    
    similarity = common_items / total_items if total_items > 0 else 0.0
    
    collab = CollabFilter(
        user1_id=user1_id,
        user2_id=user2_id,
        similarity_score=similarity
    )
    db.add(collab)
    db.commit()
    
    return {"user1_id": user1_id, "user2_id": user2_id, "similarity": similarity}

@app.get("/recommendations/{user_id}/history")
async def get_recommendation_history(user_id: int, limit: int = 20, db=Depends(get_db)):
    """Get recommendation history for user"""
    recs = db.query(Recommendation).filter(
        Recommendation.user_id == user_id
    ).order_by(Recommendation.created_at.desc()).limit(limit).all()
    
    return [
        {
            "item_id": r.item_id,
            "score": r.score,
            "reason": r.reason,
            "algorithm": r.algorithm,
            "clicked": r.clicked,
            "created_at": r.created_at
        }
        for r in recs
    ]

@app.get("/metrics")
async def get_service_metrics(db=Depends(get_db)):
    """Get service metrics"""
    user_count = db.query(User).count()
    item_count = db.query(Item).count()
    rec_count = db.query(Recommendation).count()
    avg_rating = db.query(Recommendation).with_entities(
        db.func.avg(Recommendation.score)
    ).scalar() or 0.0
    
    return {
        "users": user_count,
        "items": item_count,
        "recommendations": rec_count,
        "avg_rating": float(avg_rating),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
