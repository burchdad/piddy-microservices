# API Integration Guide - Piddy Microservices

**Complete guide for integrating Piddy's Phase 1 & 2 microservices via REST API**

## Quick Start

### 1. Start the Microservices

```bash
cd /workspaces/piddy-growth
docker-compose -f docker-compose-full-stack.yml up -d
```

### 2. Verify Services are Running

```bash
# User API (Phase 1)
curl http://localhost:8000/health

# Notification Service (Phase 2)
curl http://localhost:8001/health
```

### 3. Get an API Token

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "app@example.com",
    "password": "AppSecure123!",
    "username": "app_user"
  }'

# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "app@example.com",
    "password": "AppSecure123!"
  }' | jq '.access_token'
```

---

## Service Architecture

```
┌─────────────────────────────────────┐
│  Your Application / External System │
└────────────────┬────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
   ┌──▼──────────┐      ┌──▼─────────────────┐
   │ User API    │      │ Notification       │
   │ :8000       │      │ Service :8001      │
   │             │      │                    │
   │ • Auth      │      │ • Notifications    │
   │ • Users     │      │ • Preferences      │
   │ • RBAC      │      │ • Email            │
   │ • Audit     │      │ • Task Queue       │
   └──┬──────────┘      └──┬─────────────────┘
      │                    │
      └────────┬───────────┘
               │
        ┌──────▼──────┐
        │ PostgreSQL  │
        │ + Redis     │
        └─────────────┘
```

---

## API Endpoints Reference

### Phase 1: User API (Port 8000)

#### Base URL
```
http://localhost:8000/api/v1
```

#### Authentication Endpoints

**Register User**
```http
POST /register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "username"
}

Response: 201 Created
{
  "id": "user-uuid",
  "email": "user@example.com",
  "username": "username",
  "role": "user",
  "created_at": "2026-03-13T10:00:00Z"
}
```

**Login**
```http
POST /login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Refresh Token**
```http
POST /refresh
Authorization: Bearer <refresh_token>

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Logout**
```http
POST /logout
Authorization: Bearer <access_token>

Response: 200 OK
{ "message": "Successfully logged out" }
```

#### User Management

**Get Current User**
```http
GET /users/me
Authorization: Bearer <access_token>

Response: 200 OK
{
  "id": "user-uuid",
  "email": "user@example.com",
  "username": "username",
  "role": "user",
  "is_active": true,
  "created_at": "2026-03-13T10:00:00Z"
}
```

**List All Users** (Admin only)
```http
GET /users?skip=0&limit=20
Authorization: Bearer <admin_token>

Response: 200 OK
{
  "total": 5,
  "users": [...]
}
```

**Update User**
```http
PUT /users/{user_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "new_username",
  "is_active": true
}

Response: 200 OK
{ "status": "updated" }
```

**Delete User** (Admin only)
```http
DELETE /users/{user_id}
Authorization: Bearer <admin_token>

Response: 204 No Content
```

#### Health Check

**Health Status**
```http
GET /health

Response: 200 OK
{
  "status": "healthy",
  "service": "user-api",
  "version": "1.0.0",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

---

### Phase 2: Notification Service (Port 8001)

#### Base URL
```
http://localhost:8001
```

#### Notification Endpoints

**Create Notification**
```http
POST /notifications
Content-Type: application/json

{
  "user_id": "user-uuid",
  "notification_type": "email",
  "subject": "Welcome!",
  "message": "Your account is ready",
  "metadata": {
    "priority": "high",
    "action_url": "https://app.example.com/welcome"
  }
}

Response: 201 Created
{
  "id": "notif-uuid",
  "user_id": "user-uuid",
  "notification_type": "email",
  "subject": "Welcome!",
  "message": "Your account is ready",
  "is_read": false,
  "created_at": "2026-03-13T10:00:00Z"
}
```

**List User Notifications**
```http
GET /notifications/{user_id}?skip=0&limit=20

Response: 200 OK
{
  "user_id": "user-uuid",
  "total": 5,
  "notifications": [...]
}
```

**Mark as Read**
```http
PUT /notifications/{notification_id}/read

Response: 200 OK
{ "status": "read" }
```

**Update Notification Preferences**
```http
POST /preferences/{user_id}
Content-Type: application/json

{
  "email_notifications": true,
  "sms_notifications": false,
  "push_notifications": true,
  "digest_emails": true,
  "digest_frequency": "daily"
}

Response: 200 OK
{ "status": "preferences updated" }
```

**Service Metrics**
```http
GET /metrics

Response: 200 OK
{
  "service": "notification-service",
  "notifications_sent": 1250,
  "notifications_failed": 3,
  "queue_length": 12,
  "active_workers": 2,
  "avg_delivery_time_ms": 2847
}
```

#### Health Check

**Health Status**
```http
GET /health

Response: 200 OK
{
  "status": "healthy",
  "service": "notification-service",
  "version": "1.0.0",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

---

## Integration Patterns

### Pattern 1: User Registration + Welcome Notification

```python
import requests

# Service endpoints
USER_API = "http://localhost:8000/api/v1"
NOTIF_API = "http://localhost:8001"

# 1. Register user
user_resp = requests.post(f"{USER_API}/register", json={
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "username": "newuser"
})
user_id = user_resp.json()["id"]

# 2. Send welcome notification
notif_resp = requests.post(f"{NOTIF_API}/notifications", json={
    "user_id": user_id,
    "notification_type": "email",
    "subject": "Welcome to our platform!",
    "message": "Your account has been created successfully."
})

print(f"User created: {user_id}")
print(f"Notification sent: {notif_resp.json()['id']}")
```

### Pattern 2: Authentication Flow + API Access

```python
# 1. Get access token
login_resp = requests.post(f"{USER_API}/login", json={
    "email": "user@example.com",
    "password": "SecurePass123!"
})
token = login_resp.json()["access_token"]

# 2. Use token for protected endpoints
headers = {"Authorization": f"Bearer {token}"}
user = requests.get(f"{USER_API}/users/me", headers=headers).json()

# 3. Refresh token when expired
refresh_resp = requests.post(
    f"{USER_API}/refresh",
    headers={"Authorization": f"Bearer {refresh_token}"}
)
new_token = refresh_resp.json()["access_token"]
```

### Pattern 3: Notification with User Preferences

```python
# 1. Check user preferences
notif_api = "http://localhost:8001"
user_id = "user-uuid"

prefs = requests.get(f"{notif_api}/preferences/{user_id}").json()

# 2. Only send if user hasn't opted out
if prefs["email_notifications"]:
    requests.post(f"{notif_api}/notifications", json={
        "user_id": user_id,
        "notification_type": "email",
        "subject": "Update",
        "message": "New feature available"
    })
```

---

## Environment Configuration

### Docker Compose Override

Create `.env` file in the project root:

```env
# Database
POSTGRES_USER=piddy_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=piddy_combined

# Redis
REDIS_PASSWORD=your_redis_password_here

# JWT
JWT_SECRET=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Email (SendGrid)
SENDGRID_API_KEY=your_sendgrid_key_here

# Email (SMTP Fallback)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here

# Environment
ENV=production
```

Then use in docker-compose:

```bash
docker-compose --env-file .env -f docker-compose-full-stack.yml up -d
```

---

## Error Handling

All API responses follow standard HTTP status codes:

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | GET request successful |
| 201 | Created | Resource created |
| 204 | No Content | Deletion successful |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal error |

### Error Response Format

```json
{
  "detail": "Descriptive error message",
  "status_code": 400,
  "error_code": "INVALID_REQUEST"
}
```

### Rate Limiting Headers

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 2
X-RateLimit-Reset: 1678768800
```

---

## Monitoring & Health Checks

### Automated Health Checks

Both services expose `/health` endpoint used by container orchestration:

```bash
# Check both services
curl http://localhost:8000/health
curl http://localhost:8001/health

# For scripting
curl -f http://localhost:8000/health > /dev/null && echo "User API OK" || echo "User API DOWN"
```

### Notification Metrics

```bash
# Get service metrics
curl http://localhost:8001/metrics | jq

# Monitor queue depth
curl http://localhost:8001/metrics | jq '.queue_length'

# Delivery time
curl http://localhost:8001/metrics | jq '.avg_delivery_time_ms'
```

---

## Scaling & Production Deployment

### Horizontal Scaling

**Scale User API to 3 instances:**

```yaml
# In docker-compose.yml or Kubernetes
user-api:
  deploy:
    replicas: 3
  ports:
    - "8000-8002:8000"
```

**Behind load balancer (nginx):**

```nginx
upstream user_api {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    location /api/v1 {
        proxy_pass http://user_api;
    }
}
```

### Connection Pooling

Both services use SQLAlchemy connection pooling:
- **Pool size:** 10 connections
- **Max overflow:** 20 connections
- **Idle timeout:** 5 minutes

Automatically managed - no configuration needed.

---

## Security Considerations

### For Integrators

1. **Always use HTTPS** in production
   ```
   https://api.your-domain.com/api/v1
   ```

2. **Store tokens securely**
   - Use environment variables
   - Never commit tokens to git
   - Rotate keys regularly

3. **Implement token refresh**
   ```python
   # Refresh before expiration
   if time.time() > token_expiry - 300:  # 5 min buffer
       token = refresh_token()
   ```

4. **Validate SSL certificates**
   ```python
   requests.get(url, verify=True)  # Verify=True is default
   ```

5. **Rate limiting compliance**
   - Implement backoff strategy
   - Use exponential retry delays
   - Monitor rate limit headers

### For Operators

1. **Enable HTTPS/TLS**
   - Use Let's Encrypt for free certificates
   - Configure nginx/HAProxy termination

2. **Set strong secrets**
   - JWT_SECRET: 32+ character random string
   - Database password: Complex, unique
   - API keys: Environment-managed

3. **Monitor for attacks**
   - Rate limiting: Enabled by default
   - Audit logging: All changes tracked
   - Health monitoring: Alert on failures

---

## Testing Integration

### Quick Integration Test

```bash
#!/bin/bash
set -e

API_URL="http://localhost:8000/api/v1"
NOTIF_URL="http://localhost:8001"

echo "Testing Piddy Microservices..."

# Test 1: Health checks
echo "✓ Testing health endpoints..."
curl -f $API_URL/../health > /dev/null
curl -f $NOTIF_URL/health > /dev/null

# Test 2: User registration
echo "✓ Testing user registration..."
USER=$(curl -s -X POST $API_URL/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","username":"test"}')
USER_ID=$(echo $USER | jq -r '.id')

# Test 3: Login
echo "✓ Testing authentication..."
LOGIN=$(curl -s -X POST $API_URL/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}')
TOKEN=$(echo $LOGIN | jq -r '.access_token')

# Test 4: Notifications
echo "✓ Testing notifications..."
curl -s -X POST $NOTIF_URL/notifications \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$USER_ID\",\"notification_type\":\"email\",\"subject\":\"Test\",\"message\":\"Integration test\"}"

echo "✓ All tests passed!"
```

---

## Support & Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs -f

# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker-compose exec postgres pg_isready

# Check connection string
echo $DATABASE_URL
```

### Email Not Sending

```bash
# Verify SendGrid key is set
echo $SENDGRID_API_KEY

# Check SMTP fallback
docker-compose logs notification-service | grep -i email
```

---

## API Documentation

For detailed OpenAPI/Swagger documentation, add to the FastAPI apps:

```bash
# Swagger UI
http://localhost:8000/docs
http://localhost:8001/docs

# ReDoc documentation  
http://localhost:8000/redoc
http://localhost:8001/redoc
```

---

**This microservice is production-ready and designed for easy integration via REST API.**

For questions or issues, refer to:
- [Phase 2 Documentation](./PHASE2_DOCUMENTATION.md)
- [Quick Reference Guide](./QUICK_REFERENCE.md)
- [Architecture Overview](./HYBRID_SPRINT_COMPLETE.md)
