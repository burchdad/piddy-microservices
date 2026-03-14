"""
Social Features Service - Followers, likes, comments, social graph, interactions
Port: 8000 (standard)
Host Port: 8120
"""

import os
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/piddy_social")
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association tables
user_follower_association = Table(
    'user_followers',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('social_user.id')),
    Column('following_id', Integer, ForeignKey('social_user.id'))
)

# SQLAlchemy Models
class SocialUser(Base):
    __tablename__ = "social_user"
    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, unique=True, index=True)
    display_name = Column(String)
    bio = Column(Text)
    avatar_url = Column(String)
    followers = relationship(
        "SocialUser",
        secondary=user_follower_association,
        primaryjoin=id == user_follower_association.c.following_id,
        secondaryjoin=id == user_follower_association.c.follower_id,
        backref="following"
    )
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    content = Column(Text)
    media_urls = Column(Text)  # JSON array
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    visibility = Column(String, default="public")  # public, private, followers
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Like(Base):
    __tablename__ = "like"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    post_id = Column(Integer, ForeignKey('post.id'), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('post.id'), index=True)
    user_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    content = Column(Text)
    parent_comment_id = Column(Integer, ForeignKey('comment.id'), nullable=True)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "social_message"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    recipient_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    content = Column(Text)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Feed(Base):
    __tablename__ = "feed"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    post_id = Column(Integer, ForeignKey('post.id'), index=True)
    source_user_id = Column(Integer)  # Who created the post
    feed_type = Column(String)  # following, liked, recommended
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "social_notification"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('social_user.id'), index=True)
    from_user_id = Column(Integer)
    action = Column(String)  # followed, liked, commented, messaged
    resource_id = Column(Integer)  # post_id or message_id
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Schemas
class UserCreate(BaseModel):
    external_user_id: str
    display_name: str
    bio: str = ""
    avatar_url: str = ""

class PostCreate(BaseModel):
    user_id: int
    content: str
    media_urls: List[str] = []
    visibility: str = "public"

class CommentCreate(BaseModel):
    post_id: int
    user_id: int
    content: str
    parent_comment_id: Optional[int] = None

class MessageCreate(BaseModel):
    sender_id: int
    recipient_id: int
    content: str

# FastAPI App
app = FastAPI(title="Social Features Service", version="1.0.0")

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
        "service": "social-features",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_social_user(user: UserCreate, db=Depends(get_db)):
    """Create social user"""
    if db.query(SocialUser).filter(
        SocialUser.external_user_id == user.external_user_id
    ).first():
        raise HTTPException(status_code=400, detail="User already exists")
    
    db_user = SocialUser(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}")
async def get_user(user_id: int, db=Depends(get_db)):
    """Get user profile"""
    user = db.query(SocialUser).filter(SocialUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "follower_count": user.follower_count,
        "following_count": user.following_count,
        "created_at": user.created_at
    }

@app.post("/users/{user_id}/follow/{target_user_id}")
async def follow_user(user_id: int, target_user_id: int, db=Depends(get_db)):
    """Follow user"""
    user = db.query(SocialUser).filter(SocialUser.id == user_id).first()
    target = db.query(SocialUser).filter(SocialUser.id == target_user_id).first()
    
    if not user or not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id == target_user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Add follower relationship
    if target not in user.following:
        user.following.append(target)
        user.following_count += 1
        target.follower_count += 1
    
    # Create notification
    notif = Notification(
        user_id=target_user_id,
        from_user_id=user_id,
        action="followed"
    )
    db.add(notif)
    db.commit()
    
    return {"status": "followed", "follower_count": target.follower_count}

@app.post("/users/{user_id}/unfollow/{target_user_id}")
async def unfollow_user(user_id: int, target_user_id: int, db=Depends(get_db)):
    """Unfollow user"""
    user = db.query(SocialUser).filter(SocialUser.id == user_id).first()
    target = db.query(SocialUser).filter(SocialUser.id == target_user_id).first()
    
    if not user or not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target in user.following:
        user.following.remove(target)
        user.following_count -= 1
        target.follower_count -= 1
    
    db.commit()
    return {"status": "unfollowed", "follower_count": target.follower_count}

@app.get("/users/{user_id}/followers")
async def get_followers(user_id: int, limit: int = 20, db=Depends(get_db)):
    """Get user followers"""
    user = db.query(SocialUser).filter(SocialUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    followers = user.followers[:limit]
    return [
        {
            "id": f.id,
            "display_name": f.display_name,
            "avatar_url": f.avatar_url
        }
        for f in followers
    ]

@app.post("/posts", status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db=Depends(get_db)):
    """Create post"""
    user = db.query(SocialUser).filter(SocialUser.id == post.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_post = Post(
        user_id=post.user_id,
        content=post.content,
        media_urls=json.dumps(post.media_urls),
        visibility=post.visibility
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    # Add to follower feeds
    for follower in user.followers:
        feed_item = Feed(
            user_id=follower.id,
            post_id=db_post.id,
            source_user_id=post.user_id,
            feed_type="following"
        )
        db.add(feed_item)
    db.commit()
    
    return {"post_id": db_post.id, "created_at": db_post.created_at}

@app.get("/posts/{post_id}")
async def get_post(post_id: int, db=Depends(get_db)):
    """Get post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    user = db.query(SocialUser).filter(SocialUser.id == post.user_id).first()
    
    return {
        "id": post.id,
        "author": user.display_name,
        "content": post.content,
        "media_urls": json.loads(post.media_urls) if post.media_urls else [],
        "likes": post.like_count,
        "comments": post.comment_count,
        "created_at": post.created_at
    }

@app.post("/posts/{post_id}/like")
async def like_post(post_id: int, user_id: int, db=Depends(get_db)):
    """Like post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if already liked
    existing = db.query(Like).filter(
        Like.post_id == post_id,
        Like.user_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already liked")
    
    like = Like(post_id=post_id, user_id=user_id)
    post.like_count += 1
    
    # Create notification
    notif = Notification(
        user_id=post.user_id,
        from_user_id=user_id,
        action="liked",
        resource_id=post_id
    )
    db.add(like)
    db.add(notif)
    db.commit()
    
    return {"post_id": post_id, "likes": post.like_count}

@app.post("/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(comment_data: CommentCreate, db=Depends(get_db)):
    """Add comment to post"""
    post = db.query(Post).filter(Post.id == comment_data.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    comment = Comment(**comment_data.dict())
    post.comment_count += 1
    
    # Create notification
    notif = Notification(
        user_id=post.user_id,
        from_user_id=comment_data.user_id,
        action="commented",
        resource_id=comment_data.post_id
    )
    db.add(comment)
    db.add(notif)
    db.commit()
    db.refresh(comment)
    
    return {"comment_id": comment.id, "post_id": comment_data.post_id}

@app.get("/users/{user_id}/feed")
async def get_feed(user_id: int, limit: int = 20, db=Depends(get_db)):
    """Get user feed"""
    user = db.query(SocialUser).filter(SocialUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    feed_items = db.query(Feed).filter(
        Feed.user_id == user_id
    ).order_by(Feed.created_at.desc()).limit(limit).all()
    
    return [
        {
            "feed_id": f.id,
            "post_id": f.post_id,
            "from_user_id": f.source_user_id,
            "type": f.feed_type,
            "created_at": f.created_at
        }
        for f in feed_items
    ]

@app.post("/messages", status_code=status.HTTP_201_CREATED)
async def send_message(msg: MessageCreate, db=Depends(get_db)):
    """Send direct message"""
    sender = db.query(SocialUser).filter(SocialUser.id == msg.sender_id).first()
    recipient = db.query(SocialUser).filter(SocialUser.id == msg.recipient_id).first()
    
    if not sender or not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_msg = Message(**msg.dict())
    
    # Create notification
    notif = Notification(
        user_id=msg.recipient_id,
        from_user_id=msg.sender_id,
        action="messaged",
        resource_id=db_msg.id
    )
    db.add(db_msg)
    db.add(notif)
    db.commit()
    db.refresh(db_msg)
    
    return {"message_id": db_msg.id, "sent_at": db_msg.created_at}

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: int, unread_only: bool = False, limit: int = 20, db=Depends(get_db)):
    """Get user notifications"""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read == False)
    
    notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "from_user_id": n.from_user_id,
            "action": n.action,
            "resource_id": n.resource_id,
            "read": n.read,
            "created_at": n.created_at
        }
        for n in notifs
    ]

@app.get("/metrics")
async def get_service_metrics(db=Depends(get_db)):
    """Get service metrics"""
    user_count = db.query(SocialUser).count()
    post_count = db.query(Post).count()
    comment_count = db.query(Comment).count()
    like_count = db.query(Like).count()
    
    total_followers = db.query(
        db.func.sum(SocialUser.follower_count)
    ).scalar() or 0
    
    return {
        "users": user_count,
        "posts": post_count,
        "comments": comment_count,
        "likes": like_count,
        "total_followers": total_followers,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
