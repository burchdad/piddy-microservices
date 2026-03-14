"""
Authentication Service - Database Setup
SQLAlchemy configuration with connection pooling
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL_AUTH",
    "postgresql://piddy:piddy_secure_pwd@localhost:5432/piddy_auth"
)

# Connection pooling configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Enable UUID extension on PostgreSQL connect"""
    cursor = dbapi_conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    cursor.close()
