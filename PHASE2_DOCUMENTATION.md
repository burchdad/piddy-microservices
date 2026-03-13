# Phase 2 Implementation Documentation

## Notification Microservice - Production Architecture

### Overview

Phase 2 extends Phase 1's user management API with a complete notification microservice architecture:

- **Notification Service**: FastAPI-based microservice for notification management
- **Email Integration**: Multi-provider email delivery (SendGrid, SMTP fallback)
- **Background Queues**: Redis-based task queue for async processing
- **Database**: Separate schema in shared PostgreSQL (notifications, preferences, delivery logs)
- **CI/CD**: GitHub Actions pipeline for automated testing and deployment

### Architecture Components

#### 1. Notification Service (`notification_service.py`)

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/notifications` | Create notification |
| GET | `/notifications/{user_id}` | List user notifications |
| PUT | `/notifications/{notification_id}/read` | Mark as read |
| POST | `/preferences/{user_id}` | Update notification preferences |
| GET | `/metrics` | Service metrics |

**Features:**
- User preference validation before sending
- Automatic async queuing for delivery
- Audit trail with delivery status
- Rate limiting via Slowapi
- Service-to-service health checks

#### 2. Data Models (`models_notif.py`)

**Core Models:**

```
Notification (id, user_id, type, subject, message, delivery_status)
  ├── DeliveryLog (tracks all delivery attempts)
  └── Relationships: User (via user_id)

NotificationPreference (email, sms, push flags)
  ├── digest_emails (daily/weekly/monthly)
  └── unsubscribed_from (type-specific opt-outs)
```

**Indexes:**
- `idx_notification_user` - Fast user notification queries
- `idx_notification_type` - Filter by notification type
- `idx_notification_created` - Timeline queries
- `idx_notification_read` - Query unread count

#### 3. Email Service (`email_service.py`)

**Multi-Provider Architecture:**

```
NotificationEmail
  ├── SendGrid (primary - transactional reliability)
  ├── SMTP (fallback - Gmail, AWS SES, etc.)
  └── Automatic retry with exponential backoff
```

**Templates:**
- Welcome email
- Password reset
- Notification dispatch
- Digest emails

**Implementation Pattern:**
- Async/await throughout
- Graceful provider failure
- Delivery attempt tracking

#### 4. Queue Service (`queue_service.py`)

**Redis-Based Task Queue:**

```
Queue Names:
├── queue:notifications (primary)
├── queue:failed (retry queue)
└── Sorted sets for delayed delivery
```

**Task Lifecycle:**
1. Task queued via `queue_notification()`
2. Worker dequeues via `dequeue_notifications()`
3. On success: `mark_task_complete()`
4. On failure: `mark_task_failed()` with retry logic
5. Failed tasks moved to `queue:failed`

**Stats Endpoint:**
- Active notifications queued
- Completed delivery count
- Failed tasks for monitoring

#### 5. Docker Multi-Service Setup

**Services:**

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Persistent data |
| Redis | 6379 | Task queue + cache |
| User API | 8000 | Phase 1 service |
| Notification API | 8001 | Phase 2 service |
| pgAdmin | 5050 | Database UI |

**Health Checks:**
- All services include `HEALTHCHECK` directive
- 30s interval, 10s timeout, 3 retries
- Orchestration waits for service_healthy conditions

**Persistence:**
- PostgreSQL data volume: `postgres_data`
- Redis data volume: `redis_data`
- Network isolation: `piddy_network` bridge

### Integration Points

#### Service-to-Service Communication

**User API → Notification Service:**
```
POST /notifications
{
  "user_id": "from-user-service",
  "notification_type": "email",
  "subject": "...",
  "message": "..."
}
```

**Notification Service → Email Provider:**
```
User email fetched from preferences → SendGrid/SMTP → Delivery
```

#### Database Integration

**Shared PostgreSQL Instance:**
- Phase 1: `schema public` (users, sessions, audit_logs)
- Phase 2: `schema notifications` (notifications, preferences, delivery_logs)

**No tight coupling:** Each service owns its schema

### Security & Production Hardening

#### Phase 2 Security Enhancements:

1. **Email Provider Security**
   - SendGrid API key from environment
   - SMTP credentials never in code
   - Automatic fallback on provider failure

2. **Rate Limiting**
   - Integrated with Phase 1 limiter
   - `/notifications` endpoint: 100 qps/user

3. **Data Validation**
   - Pydantic strict validation on all inputs
   - Length limits (subject: 255, message: 5000)
   - User ID validation (36 chars max)

4. **Audit Trail**
   - All notifications logged with delivery status
   - DeliveryLog captures attempts and responses
   - Timestamp + error message on failure

### Testing Strategy

**Test Coverage:**

| Class | Tests | Coverage |
|-------|-------|----------|
| TestHealthCheck | 1 | 100% |
| TestNotificationCreation | 3 | 95% |
| TestNotificationRetrieval | 2 | 90% |
| TestNotificationPreferences | 2 | 90% |
| TestMarkAsRead | 2 | 85% |
| TestMetrics | 1 | 100% |

**Total: 11 test cases, target 85% coverage**

**Test Fixtures:**
- Sample notifications
- User preferences
- Database cleanup after each test

### CI/CD Pipeline (GitHub Actions)

**Workflow Stages:**

1. **Test Phase 1** (User API)
   - PostgreSQL service
   - pytest with coverage (85% threshold)
   - Codecov upload

2. **Test Phase 2** (Notification Service)
   - PostgreSQL + Redis services
   - pytest with coverage
   - Email service mocking

3. **Build & Push**
   - Docker multi-stage builds
   - Push to GitHub Container Registry
   - Tag with git SHA

4. **Deploy** (on main branch)
   - Deploy to staging environment
   - Run smoke tests
   - Health check validation

### Deployment Instructions

#### Local Development:

```bash
# Start full stack
docker-compose -f docker-compose-full-stack.yml up -d

# Check health
curl http://localhost:8000/health
curl http://localhost:8001/health

# View logs
docker-compose -f docker-compose-full-stack.yml logs -f

# Run tests
pytest enhanced-api-phase1/
pytest enhanced-api-phase2/
```

#### Production Deployment:

```bash
# Build images
docker build -t piddy-user-api:v1.0 ./enhanced-api-phase1
docker build -t piddy-notification-service:v1.0 ./enhanced-api-phase2

# Push to registry
docker tag piddy-user-api:v1.0 ghcr.io/your-org/piddy-user-api:v1.0
docker push ghcr.io/your-org/piddy-user-api:v1.0

# Deploy via CI/CD or orchestration tool
```

### Monitoring & Observability

#### Metrics Endpoints:

- User API: `GET /health` (Phase 1)
- Notification Service: `GET /health` (Phase 2)
- Notification Service: `GET /metrics` (queue stats)

#### Prometheus Integration:

```
# Add to Phase 2 later
from prometheus_client import Counter, Histogram

notifications_sent = Counter('notifications_sent_total', 'Total notifications sent')
delivery_time = Histogram('notification_delivery_seconds', 'Delivery time')
```

#### Logging:

- Structured JSON logging via `python-json-logger`
- Logs to stdout (captured by docker-compose)
- Stack trace on exceptions

### Next Steps (Phase 3+)

1. **Notification Templates**
   - Reusable HTML templates
   - Variable interpolation system
   - A/B testing support

2. **Event Streaming**
   - Kafka integration for user events
   - Automatic notifications on events
   - Real-time delivery tracking

3. **Analytics Dashboard**
   - Delivery metrics
   - User engagement tracking
   - Performance insights

4. **Advanced Features**
   - SMS delivery (Twilio)
   - Push notifications (FCM, APNS)
   - Webhook integrations
   - Scheduled notifications
