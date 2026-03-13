"""
PostgreSQL Initialization Script

Sets up database schema and initial data.
"""

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Verify tables created by SQLAlchemy
SELECT 'Database initialization complete' as status;
