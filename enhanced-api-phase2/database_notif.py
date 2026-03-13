"""
Notification Service Database Configuration

Uses same PostgreSQL instance but separate schema.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

# Configuration
DATABASE_URL = os.getenv(
    "NOTIFICATION_DATABASE_URL",
    "postgresql://user:password@localhost:5432/piddy_notif"
)

# Development: SQLite
if os.getenv("ENV", "development") == "development":
    DATABASE_URL = "sqlite:///./piddy_notifications.db"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "False") == "True"
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Notification database initialized")
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        raise


def drop_db():
    """Drop all tables (development only)."""
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


@event.listens_for(engine, "connect")
def handle_connect(dbapi_connection, connection_record):
    """Enable foreign keys for SQLite."""
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
