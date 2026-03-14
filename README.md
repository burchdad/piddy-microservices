# Piddy Microservices Platform

**A production-ready, fully-featured microservices platform with 27 independent services across 7 phases.**

🎯 **Status**: All services implemented, tested, and pushed to GitHub ✅  
📦 **Total Services**: 27  
💾 **Total LOC**: 20,000+ production code  
🔌 **Architecture**: Distributed microservices with independent service branches  
🐳 **Deployment**: Docker, Docker Compose, Kubernetes-ready  

---

## Quick Links

- **Full Service Catalog**: [SERVICE_CATALOG.md](SERVICE_CATALOG.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **GitHub Repository**: https://github.com/burchdad/piddy-microservices
- **Browse All Services**: 27 service branches available

---

## What is Piddy?

Piddy is a complete, enterprise-grade microservices platform designed to demonstrate:

✅ **Microservices Architecture** - 27 independent, deployable services  
✅ **Production Patterns** - Circuit breakers, retry logic, health checks, monitoring  
✅ **Scalable Design** - Each service runs independently with its own database  
✅ **Real-world Features** - Auth, payments, analytics, social, ML, and more  
✅ **Modern Stack** - FastAPI, PostgreSQL, Redis, Elasticsearch, Docker  
✅ **Professional Quality** - 20,000+ LOC of clean, documented code

---

## Services by Phase

### Phase 1: Foundation (1) | Phase 2: Communication (1)
- User API, Notifications

### Phase 3: Core Infrastructure (5)
- Authentication, Email, SMS, Push, API Gateway

### Phase 4: Advanced Infrastructure (5)
- Event Bus, Notification Hub, Webhooks, Task Queue, Secrets

### Phase 5: Analytics & Business (5)
- Analytics, Data Pipeline, Messaging, Payment, Subscription

### Phase 6: Enterprise (5)
- Search, CRM, CMS, File Storage, Monitoring

### Phase 7: AI/ML (5)
- Recommendations, Document Manager, Reports, ML Models, Social

**[See Full Catalog →](SERVICE_CATALOG.md)**

---

## Quick Start (5 minutes)

### Run All 27 Services

```bash
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git piddy
cd piddy
docker-compose up -d
curl http://localhost:8001/health  # Verify User API
```

### Run Individual Service

```bash
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git
cd analytics/enhanced-api-phase5-analytics
pip install -r requirements-phase5-analytics.txt
python routes_analytics.py
```

**[Full Deployment Guide →](DEPLOYMENT_GUIDE.md)**

---

## Repository Structure

```
piddy/
├── enhanced-api-phase{1-7}-*/          # All 27 services
├── docker-compose.yml                  # Run all services
├── SERVICE_CATALOG.md                  # Complete documentation
├── DEPLOYMENT_GUIDE.md                 # Setup instructions
└── README.md                           # This file
```

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Framework | FastAPI | 0.109.0 |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Search | Elasticsearch | 8.0+ |
| Container | Docker | Latest |

---

## Key Features

✅ **27 Independent Microservices**  
✅ **Production-Ready Code** (20,000+ LOC)  
✅ **Individual Service Branches** (easy deployment)  
✅ **Docker & Docker Compose** (local to production)  
✅ **Health Checks & Monitoring**  
✅ **API Gateway & Rate Limiting**  
✅ **Authentication & Authorization**  
✅ **Payment Processing** (Stripe/PayPal)  
✅ **Real-time Features** (WebSocket support)  
✅ **ML & Analytics** (models, recommendations)  

---

## Getting Started

1. **Clone**: `git clone -b hybrid-phase-1-2 ...`
2. **Start**: `docker-compose up -d`
3. **Verify**: `curl http://localhost:8001/health`
4. **Explore**: See [SERVICE_CATALOG.md](SERVICE_CATALOG.md)

**[Detailed Guide →](DEPLOYMENT_GUIDE.md)**

---

## Clone Options

**All Services** (Development):
```bash
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git
```

**Individual Service** (Production):
```bash
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git
```

27 service branches available for independent cloning.

---

## Service Ports

| Service | Port | Service | Port | Service | Port |
|---------|------|---------|------|---------|------|
| User API | 8001 | Analytics | 8111 | Search | 8116 |
| Notifications | 8002 | Pipeline | 8112 | CRM | 8117 |
| Auth | 8003 | Messaging | 8113 | CMS | 8118 |
| Email | 8004 | Payment | 8114 | Storage | 8119 |
| SMS | 8005 | Subscription | 8115 | Monitoring | 8120 |
| Push | 8006 | | | | |
| Gateway | 8100 | Recommendation | 8121 | ML Inference | 8124 |
| Event Bus | 8107 | Doc Manager | 8122 | Social | 8125 |
| Notification Hub | 8106 | Report Builder | 8123 | | |
| Webhook | 8108 | | | | |
| Task Queue | 8109 | | | | |
| Secrets | 8110 | | | | |

---

## Documentation

- **[SERVICE_CATALOG.md](SERVICE_CATALOG.md)** - All 27 services with models, endpoints, features
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Setup, running, troubleshooting
- **Individual Route Files** - In-code documentation and examples

---

## Development Workflow

```bash
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git
cd analytics/enhanced-api-phase5-analytics
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-phase5-analytics.txt
python routes_analytics.py  # Runs on :8000
```

Edit, test, commit, push to your service branch.

---

## Project Statistics

- **Total Services**: 27
- **Total LOC**: 20,000+
- **Service Branches**: 27
- **Phases**: 7
- **Status**: ✅ Production Ready

---

**Ready to build?** [Get started →](DEPLOYMENT_GUIDE.md)  
**Need details?** [See catalog →](SERVICE_CATALOG.md)

Last Updated: March 14, 2026
