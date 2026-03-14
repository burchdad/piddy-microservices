# Piddy Microservices Library

A comprehensive microservice architecture for the Piddy autonomous engineering platform. Each microservice is independently deployable, scalable, and focused on a single responsibility.

## 📦 Available Services

### **Service Branches** - Pull Individual Services

Clone and deploy only the services you need:

#### **Phase 1: Core User Management**
```bash
git clone -b service/user https://github.com/burchdad/piddy-microservices.git user-service
```
- **User Management API** (Port 8000)
- JWT authentication with Argon2 password hashing
- Role-based access control (RBAC)
- Rate limiting and audit logging
- Test coverage: 75%+

#### **Phase 2: Notifications**
```bash
git clone -b service/notifications https://github.com/burchdad/piddy-microservices.git notification-service
```
- **Notification Service** (Port 8001)
- Multi-channel delivery (Email, SMS, Push)
- SendGrid + SMTP with auto-failover
- Redis-based async task queue
- User preferences and delivery tracking
- Test coverage: 85%+

#### **Phase 3: Enterprise Features**

**Authentication Service**
```bash
git clone -b service/auth https://github.com/burchdad/piddy-microservices.git auth-service
```
- **Authentication Service** (Port 8002)
- OAuth2 (Google, GitHub, Microsoft, Okta)
- SAML single sign-on
- Multi-factor authentication (TOTP, SMS, Email)
- Session management with audit logging

**API Gateway**
```bash
git clone -b service/gateway https://github.com/burchdad/piddy-microservices.git api-gateway
```
- **API Gateway** (Port 8100)
- Central request routing
- Dynamic rate limiting
- CORS and request forwarding
- Service discovery and health monitoring

**Email Service**
```bash
git clone -b service/email https://github.com/burchdad/piddy-microservices.git email-service
```
- **Email Service** (Port 8003)
- HTML and plain text emails
- Template system with variable substitution
- Batch email sending
- Scheduled delivery and tracking

**SMS Service**
```bash
git clone -b service/sms https://github.com/burchdad/piddy-microservices.git sms-service
```
- **SMS Service** (Port 8004)
- Twilio/Vonage integration
- OTP generation and verification
- Batch SMS support
- Phone validation and delivery tracking

**Push Notification Service**
```bash
git clone -b service/push https://github.com/burchdad/piddy-microservices.git push-service
```
- **Push Service** (Port 8005)
- FCM (Firebase) for Android
- APNS for iOS
- Device token management
- Batch and rich push notifications

## 🚀 Quick Start

### Option 1: Single Service
```bash
git clone -b service/user https://github.com/burchdad/piddy-microservices.git
cd enhanced-api-phase1
pip install -r requirements-phase1.txt
export DATABASE_URL=postgresql://...
python routes.py
```

### Option 2: All Services (Docker Compose)
```bash
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git
docker-compose -f docker-compose-phase3.yml up
```

### Option 3: Custom Mix
```bash
git clone -b service/user https://github.com/burchdad/piddy-microservices.git user-api
git clone -b service/auth https://github.com/burchdad/piddy-microservices.git auth-svc
git clone -b service/email https://github.com/burchdad/piddy-microservices.git email-svc
```

## 📋 Branch Structure

| Branch | Purpose | Content |
|--------|---------|---------|
| `main` | Library Overview | This README |
| `service/user` | User API | Phase 1 |
| `service/notifications` | Notifications | Phase 2 |
| `service/auth` | Authentication | Phase 3 Auth |
| `service/gateway` | API Gateway | Phase 3 Gateway |
| `service/email` | Email Service | Phase 3 Email |
| `service/sms` | SMS Service | Phase 3 SMS |
| `service/push` | Push Service | Phase 3 Push |
| `hybrid-phase-1-2` | Full Stack | Reference/Testing |

## 🔧 Technology Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Cache/Queue:** Redis
- **Container:** Docker
- **Password Hashing:** Argon2
- **Auth:** JWT + OAuth2
- **Testing:** pytest (75%+ coverage)

## 📊 Performance Targets

| Service | Memory | CPU | Max RPS | Response |
|---------|--------|-----|---------|----------|
| User API | 512MB | 2c | 500 | 100-200ms |
| Gateway | 128MB | 1c | 5000 | 10-50ms |
| Auth | 256MB | 1c | 500 | 100-200ms |
| Email | 256MB | 1c | 1000 | 100-300ms |
| SMS | 256MB | 1c | 1000 | 100-300ms |
| Push | 256MB | 1c | 2000 | 50-150ms |

## ✨ Key Features

✅ Microservices architecture
✅ Independent databases per service
✅ OAuth2 with 4+ providers
✅ Multi-factor authentication
✅ Multi-channel notifications
✅ API gateway with rate limiting
✅ Async task processing
✅ Comprehensive test coverage
✅ Production-ready Docker builds
✅ Health checks and metrics

## 🤝 Contributing

1. Clone a service: `git clone -b service/SERVICE_NAME`
2. Make changes
3. Run tests: `pytest --cov`
4. Commit and push
5. Create pull request

## 📄 License

Proprietary - Piddy Autonomous Engineering Platform

---

**Status:** Production Ready | **Last Updated:** March 14, 2026
