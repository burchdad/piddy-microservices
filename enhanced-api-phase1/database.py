"""
Database Configuration and Setup

Using SQLAlchemy ORM with PostgreSQL for production-ready data persistence.
Supports both PostgreSQL and SQLite for development/testing.
"""

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./piddy_users.db"  # Default to SQLite for development
)

# For production, use:
# DATABASE_URL = "postgresql://user:password@localhost/piddy_users"

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,  # Test connections before use
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Dependency for FastAPI to inject database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database access outside of FastAPI context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (for testing/development)."""
    Base.metadata.drop_all(bind=engine)
