# Piddy Microservices Platform - Complete Service Catalog

**Project Status**: 27 Microservices across 7 Phases | All services deployed and pushed to GitHub  
**Total LOC**: 20,000+ production code | **Git Branches**: 29 (27 services + hybrid + main)  
**Repository**: https://github.com/burchdad/piddy-microservices

---

## Quick Access

- **Clone All Services**: `git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git`
- **Clone Individual Service**: `git clone -b service/{name} https://github.com/burchdad/piddy-microservices.git`
- **Run All Services**: See Docker Compose section below

---

## Phase 1: Foundation (1 Service)

### 1. User API Service
- **Branch**: `service/user`
- **Port**: 8001 (host) / 8000 (internal)
- **Models**: User, UserProfile, Roles, Permissions
- **Key Endpoints**:
  - `POST /register` - User registration
  - `POST /login` - Authentication
  - `GET /users/{id}` - User details
  - `PUT /users/{id}` - Update profile
  - `POST /roles` - Role management
  - `GET /permissions` - Permission listing
- **Database**: PostgreSQL
- **Cache**: Redis (session management)
- **Auth**: JWT tokens
- **Status**: ✅ Production Ready

---

## Phase 2: Notifications (1 Service)

### 2. Notification Service
- **Branch**: `service/notifications`
- **Port**: 8002 (host) / 8000 (internal)
- **Models**: Notification, NotificationTemplate, Queue, DeliveryLog
- **Key Endpoints**:
  - `POST /notifications/send` - Send notification
  - `GET /notifications/{user_id}` - List notifications
  - `PUT /notifications/{id}/read` - Mark as read
  - `POST /queue/process` - Background queue processing
  - `GET /templates` - Notification templates
- **Queue**: Redis/RabbitMQ
- **Integrations**: Email, SMS, Push
- **Status**: ✅ Production Ready

---

## Phase 3: Core Services (5 Services)

### 3. Authentication Service
- **Branch**: `service/auth`
- **Port**: 8003 (host) / 8000 (internal)
- **Models**: User, Token, Session, MFAToken, OAuthProvider
- **Key Endpoints**:
  - `POST /auth/login` - Login
  - `POST /auth/mfa/verify` - MFA verification
  - `POST /auth/oauth/{provider}` - OAuth login
  - `POST /auth/refresh` - Token refresh
  - `POST /auth/logout` - Logout
  - `GET /auth/session/{token}` - Session validation
- **Features**: JWT, MFA, OAuth2, Session management
- **License**: MIT
- **Status**: ✅ Production Ready

### 4. Email Service
- **Branch**: `service/email`
- **Port**: 8004 (host) / 8000 (internal)
- **Models**: EmailTemplate, EmailLog, Attachment
- **Key Endpoints**:
  - `POST /send` - Send email
  - `POST /templates` - Create template
  - `GET /logs` - Email history
  - `POST /verify-webhook` - Provider webhooks
- **Providers**: SendGrid, AWS SES, SMTP
- **Features**: Templates, attachments, batching
- **Status**: ✅ Production Ready

### 5. SMS Service
- **Branch**: `service/sms`
- **Port**: 8005 (host) / 8000 (internal)
- **Models**: SMSTemplate, SMSLog, PhoneNumber
- **Key Endpoints**:
  - `POST /send` - Send SMS
  - `GET /templates` - SMS templates
  - `GET /logs` - SMS history
  - `POST /webhook` - Delivery webhooks
- **Providers**: Twilio, AWS SNS
- **Features**: Message queuing, delivery tracking
- **Status**: ✅ Production Ready

### 6. Push Notification Service
- **Branch**: `service/push`
- **Port**: 8006 (host) / 8000 (internal)
- **Models**: Device, PushNotification, Campaign, DeliveryStatus
- **Key Endpoints**:
  - `POST /register-device` - Device registration
  - `POST /send` - Send push
  - `GET /campaigns` - Campaign management
  - `GET /analytics` - Delivery analytics
- **Platforms**: iOS, Android, Web
- **Providers**: Firebase Cloud Messaging
- **Status**: ✅ Production Ready

### 7. API Gateway
- **Branch**: `service/gateway`
- **Port**: 8100 (host) / 8000 (internal)
- **Features**: Request routing, rate limiting, authentication
- **Key Endpoints**:
  - Forwards to all microservices
  - Rate limiting (1000 req/min per user)
  - Request/response logging
  - Circuit breaker patterns
- **Status**: ✅ Production Ready

---

## Phase 4: Infrastructure Services (5 Services)

### 8. Event Bus Service
- **Branch**: `service/event-bus`
- **Port**: 8107 (host) / 8000 (internal)
- **Models**: Event, EventSchema, Subscription, EventLog
- **Key Endpoints**:
  - `POST /events/publish` - Publish event
  - `POST /events/subscribe` - Subscribe to events
  - `GET /events/history` - Event history
  - `GET /schemas` - Event schemas
- **Pattern**: Pub/Sub
- **Backend**: Redis/RabbitMQ
- **Status**: ✅ Production Ready

### 9. Notification Hub Service
- **Branch**: `service/notification-hub`
- **Port**: 8106 (host) / 8000 (internal)
- **Models**: Template, Channel, Broadcast, DeliveryTracker
- **Key Endpoints**:
  - `POST /broadcasts/create` - Create broadcast
  - `POST /templates/create` - Template creation
  - `GET /channels` - Available channels
  - `GET /metrics` - Delivery metrics
- **Channels**: Email, SMS, Push, In-App
- **Status**: ✅ Production Ready

### 10. Webhook Service
- **Branch**: `service/webhook`
- **Port**: 8108 (host) / 8000 (internal)
- **Models**: Webhook, WebhookEvent, DeliveryAttempt, Signature
- **Key Endpoints**:
  - `POST /register` - Register webhook
  - `POST /test/{id}` - Test webhook
  - `GET /deliveries` - Delivery history
  - `POST /retry/{id}` - Retry delivery
- **Features**: HMAC signatures, retry logic, dead letter queue
- **Status**: ✅ Production Ready

### 11. Task Queue Service
- **Branch**: `service/task-queue`
- **Port**: 8109 (host) / 8000 (internal)
- **Models**: Task, Job, WorkerPool, ExecutionLog
- **Key Endpoints**:
  - `POST /tasks/enqueue` - Add task
  - `GET /tasks/{id}/status` - Task status
  - `POST /tasks/retry` - Retry failed task
  - `GET /workers` - Worker status
- **Backend**: Celery/Redis
- **Features**: Retry logic, scheduling, worker management
- **Status**: ✅ Production Ready

### 12. Secrets Management Service
- **Branch**: `service/secrets`
- **Port**: 8110 (host) / 8000 (internal)
- **Models**: Secret, SecretVersion, AccessLog, RotationPolicy
- **Key Endpoints**:
  - `POST /secrets` - Store secret
  - `GET /secrets/{id}` - Retrieve secret
  - `POST /secrets/{id}/rotate` - Rotate secret
  - `GET /audit` - Access audit log
  - `POST /secrets/{id}/share` - Share secret
- **Encryption**: AES-256
- **Audit**: Complete access logging
- **Status**: ✅ Production Ready

---

## Phase 5: Analytics & Business Services (5 Services)

### 13. Analytics Service
- **Branch**: `service/analytics`
- **Port**: 8111 (host) / 8000 (internal)
- **Models**: Event, Metric, Dashboard, Cohort, Funnel
- **Key Endpoints**:
  - `POST /events/ingest` - Event ingestion
  - `GET /metrics/query` - Query metrics
  - `POST /dashboards` - Create dashboard
  - `GET /cohorts` - User cohorts
  - `GET /funnels` - Funnel analysis
- **Features**: Real-time metrics, time-series, segmentation, exports
- **Database**: PostgreSQL + TimescaleDB
- **Status**: ✅ Production Ready

### 14. Data Pipeline Service
- **Branch**: `service/pipeline`
- **Port**: 8112 (host) / 8000 (internal)
- **Models**: PipelineJob, Transformation, DataSource, Schema, JobHistory
- **Key Endpoints**:
  - `POST /jobs/create` - Create pipeline job
  - `POST /jobs/{id}/run` - Execute job
  - `GET /jobs/{id}/status` - Job status
  - `POST /transformations/validate` - Validate schema
  - `GET /history` - Execution history
- **Features**: ETL/ELT, schema validation, error handling, notifications
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

### 15. Messaging & Chat Service
- **Branch**: `service/messaging`
- **Port**: 8113 (host) / 8000 (internal)
- **Models**: Message, Channel, Conversation, ReadReceipt, UserPresence
- **Key Endpoints**:
  - `POST /messages/send` - Send message
  - `GET /conversations` - List conversations
  - `POST /channels/create` - Create channel
  - `GET /presence` - User presence
  - `GET /messages/search` - Message search
- **Features**: Real-time messaging, channels, typing indicators, read receipts
- **WebSocket**: Real-time support
- **Status**: ✅ Production Ready

### 16. Payment Processing Service
- **Branch**: `service/payment`
- **Port**: 8114 (host) / 8000 (internal)
- **Models**: Payment, Invoice, Refund, Transaction, PaymentMethod, Webhook
- **Key Endpoints**:
  - `POST /payments/create` - Create payment
  - `POST /payments/refund` - Refund payment
  - `GET /invoices` - List invoices
  - `POST /transactions/verify` - Verify transaction
  - `POST /webhook` - Payment provider webhook
- **Providers**: Stripe, PayPal
- **Features**: Invoice generation, refunds, webhooks, PCI compliance
- **Status**: ✅ Production Ready

### 17. Subscription Management Service
- **Branch**: `service/subscription`
- **Port**: 8115 (host) / 8000 (internal)
- **Models**: Subscription, Plan, BillingCycle, Usage, Feature, Entitlement
- **Key Endpoints**:
  - `POST /plans/create` - Create plan
  - `POST /subscriptions/create` - Subscribe user
  - `POST /subscriptions/{id}/upgrade` - Upgrade plan
  - `GET /usage` - Usage tracking
  - `GET /entitlements` - Enabled features
- **Features**: Multi-tier SaaS, usage tracking, auto-renewal, feature gating
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

---

## Phase 6: Enterprise Services (5 Services)

### 18. Full-Text Search Service
- **Branch**: `service/search`
- **Port**: 8116 (host) / 8000 (internal)
- **Models**: SearchIndex, Query, Result, Facet, Suggestion
- **Key Endpoints**:
  - `GET /search` - Full-text search
  - `POST /index` - Index document
  - `GET /suggestions` - Auto-complete
  - `GET /facets` - Faceted search
  - `POST /reindex` - Rebuild index
- **Engine**: Elasticsearch
- **Features**: Faceted search, filters, aggregations, suggestions
- **Status**: ✅ Production Ready

### 19. CRM Service
- **Branch**: `service/crm`
- **Port**: 8117 (host) / 8000 (internal)
- **Models**: Contact, Interaction, Deal, Pipeline, Activity, Note
- **Key Endpoints**:
  - `POST /contacts/create` - Add contact
  - `POST /interactions/log` - Log interaction
  - `POST /deals/create` - Create deal
  - `GET /pipelines/{id}` - Deal pipeline
  - `GET /activities` - Activity history
- **Features**: Contact management, deal tracking, interaction logging
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

### 20. Content Management Service (CMS)
- **Branch**: `service/cms`
- **Port**: 8118 (host) / 8000 (internal)
- **Models**: Article, Page, Media, PublishingWorkflow, ContentVersion, Schedule
- **Key Endpoints**:
  - `POST /articles/create` - Create article
  - `POST /publications/publish` - Publish content
  - `POST /media/upload` - Upload media
  - `GET /versions/{id}` - Content history
  - `POST /schedule` - Schedule publishing
- **Features**: WYSIWYG/Markdown editing, versioning, workflows, scheduling
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

### 21. File Storage Service
- **Branch**: `service/storage`
- **Port**: 8119 (host) / 8000 (internal)
- **Models**: File, Folder, AccessControl, FileVersion, CDNUrl
- **Key Endpoints**:
  - `POST /files/upload` - Upload file
  - `GET /files/download/{id}` - Download file
  - `POST /folders/create` - Create folder
  - `GET /cdn-url` - Get CDN URL
  - `POST /access/grant` - Share file
- **Backend**: S3-compatible storage (MinIO/AWS)
- **Features**: Versioning, access control, CDN, scanning
- **Status**: ✅ Production Ready

### 22. Monitoring & Alerts Service
- **Branch**: `service/monitoring`
- **Port**: 8120 (host) / 8000 (internal)
- **Models**: HealthCheck, AlertRule, Incident, Metric, ServiceStatus, Alert
- **Key Endpoints**:
  - `GET /health` - Service health
  - `POST /alerts/create` - Create alert rule
  - `GET /incidents` - Active incidents
  - `GET /metrics` - Performance metrics
  - `POST /notifications` - Send alert
- **Features**: Health monitoring, alerting, incident management, dashboards
- **Database**: PostgreSQL + Prometheus
- **Status**: ✅ Production Ready

---

## Phase 7: AI/ML & Advanced Services (5 Services)

### 23. Recommendation Engine Service
- **Branch**: `service/recommendation`
- **Port**: 8121 (host) / 8000 (internal)
- **Models**: Recommendation, UserProfile, ItemVector, CollaborativeFilter, Ranking
- **Key Endpoints**:
  - `POST /recommend` - Get recommendations
  - `POST /feedback` - Log user feedback
  - `POST /train` - Train models
  - `GET /similar/{item_id}` - Similar items
  - `POST /rerank` - Rerank results
- **Algorithms**: Collaborative filtering, content-based, hybrid
- **ML Framework**: Scikit-learn, TensorFlow
- **Status**: ✅ Production Ready

### 24. Document Management Service
- **Branch**: `service/document-manager`
- **Port**: 8122 (host) / 8000 (internal)
- **Models**: Document, DocumentVersion, Annotation, AccessLog, Metadata
- **Key Endpoints**:
  - `POST /documents/upload` - Upload document
  - `GET /documents/search` - Search documents
  - `POST /documents/annotate` - Add annotations
  - `GET /metadata` - Extract metadata
  - `POST /ocr` - OCR processing
- **Features**: OCR, full-text search, annotations, versioning, metadata extraction
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

### 25. Report Builder Service
- **Branch**: `service/report-builder`
- **Port**: 8123 (host) / 8000 (internal)
- **Models**: Report, Template, DataSource, ChartConfig, Schedule, Distribution
- **Key Endpoints**:
  - `POST /reports/create` - Create report
  - `POST /templates` - Create template
  - `GET /reports/generate` - Generate report
  - `POST /schedule` - Schedule report
  - `POST /distribute` - Email/share report
- **Features**: Dynamic reports, templates, scheduling, exports (PDF, Excel, PNG)
- **Database**: PostgreSQL
- **Status**: ✅ Production Ready

### 26. ML Model Inference Service
- **Branch**: `service/ml-inference`
- **Port**: 8124 (host) / 8000 (internal)
- **Models**: Model, Prediction, FeatureVector, PredictionLog, ModelVersion
- **Key Endpoints**:
  - `POST /predict` - Make prediction
  - `POST /models/deploy` - Deploy model
  - `GET /models` - List models
  - `POST /batch/predict` - Batch predictions
  - `GET /metrics` - Model metrics
- **Frameworks**: TensorFlow, PyTorch, scikit-learn
- **Features**: Model versioning, A/B testing, monitoring
- **Status**: ✅ Production Ready

### 27. Social Features Service
- **Branch**: `service/social`
- **Port**: 8125 (host) / 8000 (internal)
- **Models**: User, Follow, Like, Comment, Post, ActivityFeed, Notification
- **Key Endpoints**:
  - `POST /posts/create` - Create post
  - `POST /follow` - Follow user
  - `POST /like` - Like post/comment
  - `POST /comments` - Add comment
  - `GET /feed` - Activity feed
  - `GET /notifications` - Social notifications
- **Features**: Following, likes, comments, activity feeds, notifications
- **Database**: PostgreSQL
- **Caching**: Redis (feed caching)
- **Status**: ✅ Production Ready

---

## Service Matrix

| Phase | Service | Port | Branch | Models | Endpoints | Status |
|-------|---------|------|--------|--------|-----------|--------|
| 1 | User API | 8001 | service/user | 3 | 12+ | ✅ |
| 2 | Notifications | 8002 | service/notifications | 4 | 10+ | ✅ |
| 3 | Authentication | 8003 | service/auth | 5 | 10+ | ✅ |
| 3 | Email | 8004 | service/email | 3 | 8+ | ✅ |
| 3 | SMS | 8005 | service/sms | 3 | 7+ | ✅ |
| 3 | Push | 8006 | service/push | 4 | 8+ | ✅ |
| 3 | Gateway | 8100 | service/gateway | - | Routing | ✅ |
| 4 | Event Bus | 8107 | service/event-bus | 4 | 8+ | ✅ |
| 4 | Notification Hub | 8106 | service/notification-hub | 4 | 8+ | ✅ |
| 4 | Webhook | 8108 | service/webhook | 4 | 8+ | ✅ |
| 4 | Task Queue | 8109 | service/task-queue | 4 | 8+ | ✅ |
| 4 | Secrets | 8110 | service/secrets | 4 | 8+ | ✅ |
| 5 | Analytics | 8111 | service/analytics | 5 | 10+ | ✅ |
| 5 | Pipeline | 8112 | service/pipeline | 5 | 10+ | ✅ |
| 5 | Messaging | 8113 | service/messaging | 5 | 10+ | ✅ |
| 5 | Payment | 8114 | service/payment | 6 | 10+ | ✅ |
| 5 | Subscription | 8115 | service/subscription | 7 | 10+ | ✅ |
| 6 | Search | 8116 | service/search | 4 | 8+ | ✅ |
| 6 | CRM | 8117 | service/crm | 6 | 10+ | ✅ |
| 6 | CMS | 8118 | service/cms | 6 | 10+ | ✅ |
| 6 | Storage | 8119 | service/storage | 5 | 10+ | ✅ |
| 6 | Monitoring | 8120 | service/monitoring | 6 | 10+ | ✅ |
| 7 | Recommendation | 8121 | service/recommendation | 5 | 8+ | ✅ |
| 7 | Document Manager | 8122 | service/document-manager | 5 | 10+ | ✅ |
| 7 | Report Builder | 8123 | service/report-builder | 6 | 10+ | ✅ |
| 7 | ML Inference | 8124 | service/ml-inference | 5 | 8+ | ✅ |
| 7 | Social | 8125 | service/social | 7 | 10+ | ✅ |

---

## Technology Stack

### Core Framework
- **FastAPI** 0.109.0 - Async API framework
- **Python** 3.11 - Language
- **Uvicorn** - ASGI server

### Database
- **PostgreSQL** 16 - Primary database
- **Redis** 7 - Caching & sessions
- **Elasticsearch** 8.0+ - Full-text search
- **TimescaleDB** - Time-series data

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Orchestration
- **Git/GitHub** - Version control

### Libraries (All Services)
- SQLAlchemy 2.0.23
- Pydantic 2.0+
- pytest 7.4.3
- python-jose
- passlib[bcrypt]
- python-multipart
- stripe 9.1.1+
- boto3 1.26.0+
- elasticsearch 8.0+
- requests
- aiohttp
- celery
- redis

---

## Getting Started

### Clone All Services
```bash
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git piddy
cd piddy
```

### Clone Individual Service
```bash
git clone -b service/{name} https://github.com/burchdad/piddy-microservices.git {name}-service
cd {name}-service
```

### Run Individual Service
```bash
cd enhanced-api-phase{X}-{service}
pip install -r requirements-phase{X}-{service}.txt
python routes_{service}.py
```

### Docker
```bash
cd enhanced-api-phase{X}-{service}
docker build -t service-{name} .
docker run -p 8{XXX}:8000 service-{name}
```

---

## Support & Documentation

- **Repository**: https://github.com/burchdad/piddy-microservices
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Main Branch**: Contains all services
- **Service Branches**: Individual service branches for isolated deployment

---

**Last Updated**: March 14, 2026  
**All 27 Services Tested & Deployed** ✅
