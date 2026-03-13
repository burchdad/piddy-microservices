# Database Schema Patterns

## Entity-Relationship Pattern

```sql
-- Core entity pattern
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_type (type),
    INDEX idx_created (created_at)
);

-- Relationship pattern with attributes
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    source_id UUID REFERENCES entities(id),
    target_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_source (source_id),
    INDEX idx_target (target_id),
    INDEX idx_type (relationship_type)
);
```

## Performance Patterns
- Use UUID for global uniqueness
- Index foreign keys and frequently queried fields
- Store JSON metadata for flexibility
- Include audit timestamps
- Denormalize for read-heavy workloads

## Caching Strategy Pattern
- Cache frequently accessed entities
- Invalidate on updates
- Use time-based expiration (TTL)
- Monitor cache hit rates

---
Pattern Type: Database Design
Best For: Knowledge graphs, entity relationships
