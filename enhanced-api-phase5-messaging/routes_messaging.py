"""
Messaging/Chat Service - Real-time messaging and conversations
Port: 8000 (standard)
Host Port: 8108
"""
import os
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Query
import uvicorn

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://piddy:piddy@postgres:5432/piddy_messaging")
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    channel_name = Column(String(200), index=True)
    channel_type = Column(String(100))  # direct, group, public, private
    description = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    member_count = Column(Integer, default=0)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, index=True)
    sender_id = Column(String(100), index=True)
    content = Column(Text)
    message_type = Column(String(50), default="text")  # text, image, file, system
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    reactions = Column(Text, default="{}")
    
    __table_args__ = (
        Index('idx_channel_created', 'channel_id', 'created_at'),
    )

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    conversation_name = Column(String(200), index=True)
    conversation_type = Column(String(100))  # dm, group
    participants = Column(Text)  # JSON list of user IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime)
    message_count = Column(Integer, default=0)

class ReadReceipt(Base):
    __tablename__ = "read_receipts"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, index=True)
    user_id = Column(String(100), index=True)
    read_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_message_user', 'message_id', 'user_id'),
    )

class ChannelMember(Base):
    __tablename__ = "channel_members"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, index=True)
    user_id = Column(String(100), index=True)
    role = Column(String(50), default="member")  # member, moderator, admin
    joined_at = Column(DateTime, default=datetime.utcnow)
    muted = Column(Boolean, default=False)
    last_read_at = Column(DateTime)
    unread_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_channel_user', 'channel_id', 'user_id'),
    )

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String(100), index=True)
    recipient_id = Column(String(100), index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class ChannelCreate(BaseModel):
    channel_name: str
    channel_type: str
    description: str = None
    created_by: str

class MessageCreate(BaseModel):
    channel_id: int
    sender_id: str
    content: str
    message_type: str = "text"

class DirectMessageCreate(BaseModel):
    sender_id: str
    recipient_id: str
    content: str

class ConversationCreate(BaseModel):
    conversation_name: str
    conversation_type: str
    participants: list

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

# FastAPI App
app = FastAPI(title="Messaging Service", version="1.0.0")

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow()
    }

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Get service metrics"""
    channel_count = db.query(Channel).count()
    message_count = db.query(Message).count()
    active_channels = db.query(Channel).filter(Channel.is_archived == False).count()
    conversation_count = db.query(Conversation).count()
    
    return {
        "total_channels": channel_count,
        "total_messages": message_count,
        "active_channels": active_channels,
        "total_conversations": conversation_count,
        "timestamp": datetime.utcnow()
    }

# Channel Endpoints
@app.post("/channels")
def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Create new channel"""
    db_channel = Channel(
        channel_name=channel.channel_name,
        channel_type=channel.channel_type,
        description=channel.description,
        created_by=channel.created_by
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    
    return {
        "id": db_channel.id,
        "channel_name": db_channel.channel_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/channels")
def list_channels(archived: bool = Query(False), db: Session = Depends(get_db)):
    """List all channels"""
    query = db.query(Channel).filter(Channel.is_archived == archived)
    channels = query.all()
    
    return {
        "total": len(channels),
        "channels": channels,
        "timestamp": datetime.utcnow()
    }

@app.get("/channels/{channel_id}")
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get channel details"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    member_count = db.query(ChannelMember).filter(ChannelMember.channel_id == channel_id).count()
    
    return {
        "id": channel.id,
        "channel_name": channel.channel_name,
        "channel_type": channel.channel_type,
        "member_count": member_count,
        "created_at": channel.created_at,
        "timestamp": datetime.utcnow()
    }

@app.post("/channels/{channel_id}/join")
def join_channel(channel_id: int, user_id: str, db: Session = Depends(get_db)):
    """Join channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    existing = db.query(ChannelMember).filter(
        ChannelMember.channel_id == channel_id,
        ChannelMember.user_id == user_id
    ).first()
    
    if not existing:
        member = ChannelMember(
            channel_id=channel_id,
            user_id=user_id
        )
        db.add(member)
        channel.member_count += 1
        db.commit()
    
    return {
        "channel_id": channel_id,
        "user_id": user_id,
        "status": "joined",
        "timestamp": datetime.utcnow()
    }

# Message Endpoints
@app.post("/channels/{channel_id}/messages")
def send_message(channel_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    """Send message to channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    db_message = Message(
        channel_id=channel_id,
        sender_id=message.sender_id,
        content=message.content,
        message_type=message.message_type
    )
    db.add(db_message)
    channel.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_message)
    
    return {
        "id": db_message.id,
        "channel_id": channel_id,
        "sender_id": message.sender_id,
        "created_at": db_message.created_at,
        "timestamp": datetime.utcnow()
    }

@app.get("/channels/{channel_id}/messages")
def get_channel_messages(
    channel_id: int,
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get messages from channel"""
    messages = db.query(Message).filter(
        Message.channel_id == channel_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "channel_id": channel_id,
        "count": len(messages),
        "messages": messages,
        "timestamp": datetime.utcnow()
    }

@app.delete("/messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    """Delete message"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_deleted = True
    db.commit()
    
    return {
        "message_id": message_id,
        "status": "deleted",
        "timestamp": datetime.utcnow()
    }

# Read Receipts Endpoints
@app.post("/messages/{message_id}/read")
def mark_message_read(message_id: int, user_id: str, db: Session = Depends(get_db)):
    """Mark message as read"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    receipt = db.query(ReadReceipt).filter(
        ReadReceipt.message_id == message_id,
        ReadReceipt.user_id == user_id
    ).first()
    
    if not receipt:
        receipt = ReadReceipt(
            message_id=message_id,
            user_id=user_id
        )
        db.add(receipt)
        db.commit()
    
    return {
        "message_id": message_id,
        "user_id": user_id,
        "status": "read",
        "read_at": receipt.read_at,
        "timestamp": datetime.utcnow()
    }

@app.get("/messages/{message_id}/read-receipts")
def get_read_receipts(message_id: int, db: Session = Depends(get_db)):
    """Get read receipts for message"""
    receipts = db.query(ReadReceipt).filter(ReadReceipt.message_id == message_id).all()
    
    return {
        "message_id": message_id,
        "read_count": len(receipts),
        "receipts": receipts,
        "timestamp": datetime.utcnow()
    }

# Direct Message Endpoints
@app.post("/direct-messages")
def send_direct_message(dm: DirectMessageCreate, db: Session = Depends(get_db)):
    """Send direct message"""
    db_dm = DirectMessage(
        sender_id=dm.sender_id,
        recipient_id=dm.recipient_id,
        content=dm.content
    )
    db.add(db_dm)
    db.commit()
    db.refresh(db_dm)
    
    return {
        "id": db_dm.id,
        "sender_id": dm.sender_id,
        "recipient_id": dm.recipient_id,
        "created_at": db_dm.created_at,
        "timestamp": datetime.utcnow()
    }

@app.get("/direct-messages/{user_id}")
def get_direct_messages(
    user_id: str,
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get direct messages for user"""
    messages = db.query(DirectMessage).filter(
        (DirectMessage.sender_id == user_id) | (DirectMessage.recipient_id == user_id)
    ).order_by(DirectMessage.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "user_id": user_id,
        "count": len(messages),
        "messages": messages,
        "timestamp": datetime.utcnow()
    }

@app.post("/direct-messages/{message_id}/read")
def mark_dm_read(message_id: int, db: Session = Depends(get_db)):
    """Mark direct message as read"""
    dm = db.query(DirectMessage).filter(DirectMessage.id == message_id).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Direct message not found")
    
    dm.read = True
    dm.read_at = datetime.utcnow()
    db.commit()
    
    return {
        "message_id": message_id,
        "status": "read",
        "read_at": dm.read_at,
        "timestamp": datetime.utcnow()
    }

# Conversation Endpoints
@app.post("/conversations")
def create_conversation(conv: ConversationCreate, db: Session = Depends(get_db)):
    """Create conversation"""
    db_conv = Conversation(
        conversation_name=conv.conversation_name,
        conversation_type=conv.conversation_type,
        participants=json.dumps(conv.participants)
    )
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)
    
    return {
        "id": db_conv.id,
        "conversation_name": db_conv.conversation_name,
        "status": "created",
        "timestamp": datetime.utcnow()
    }

@app.get("/conversations")
def list_conversations(user_id: str = Query(None), db: Session = Depends(get_db)):
    """List conversations"""
    conversations = db.query(Conversation).all()
    
    return {
        "total": len(conversations),
        "conversations": conversations,
        "timestamp": datetime.utcnow()
    }

@app.get("/conversations/{conversation_id}/members")
def get_conversation_members(conversation_id: int, db: Session = Depends(get_db)):
    """Get conversation members"""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    participants = json.loads(conv.participants)
    
    return {
        "conversation_id": conversation_id,
        "member_count": len(participants),
        "participants": participants,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
