# API Design Patterns

## REST Endpoint Design

```python
# Pattern: RESTful CRUD operations with proper HTTP verbs
class APIPattern:
    """
    - GET /resource - List resources
    - POST /resource - Create new resource
    - GET /resource/{id} - Get specific resource
    - PUT /resource/{id} - Update resource
    - DELETE /resource/{id} - Delete resource
    """
```

## Response Envelope Pattern

```json
{
  "status": "success|error|warning",
  "data": {
    "result": "actual_data",
    "timestamp": "2026-03-13T04:15:00Z"
  },
  "metadata": {
    "version": "1.0",
    "cache_hit": true
  },
  "errors": []
}
```

## API Versioning Strategy
- Maintain backward compatibility for 2 major versions
- Use URL versioning: `/api/v1/`, `/api/v2/`
- Document breaking changes prominently
- Provide migration guides for deprecated endpoints

## Error Handling Pattern
- Use standard HTTP status codes
- Include error codes for programmatic handling
- Provide context and suggestions for resolution
- Log errors for debugging

---
Document Type: Architecture Pattern
Status: Documented
Version: 1.0
