# Piddy Microservices - Deployment & Quick Start Guide

## Overview

Piddy is a complete, production-ready microservices platform with **27 independent services** across 7 phases. Every service is fully isolated, tested, and ready to deploy.

**Repository**: https://github.com/burchdad/piddy-microservices  
**Status**: All services pushed to GitHub ✅  
**Total LOC**: 20,000+ production code

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start-5-minutes)
2. [Clone Strategies](#clone-strategies)
3. [Run Individual Service](#run-individual-service)
4. [Run All Services (Docker)](#run-all-services-docker)
5. [Service Verification](#service-verification)
6. [Troubleshooting](#troubleshooting)
7. [Development Workflow](#development-workflow)

---

## Quick Start (5 minutes)

### Option A: Run All 27 Services Locally

```bash
# 1. Clone the repository
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git piddy
cd piddy

# 2. Start all services with Docker Compose
docker-compose up -d

# 3. Verify all services are running
docker-compose ps

# 4. Check service health
curl http://localhost:8001/health  # User API
curl http://localhost:8002/health  # Notifications
curl http://localhost:8003/health  # Auth
# ... etc (see SERVICE_CATALOG.md for all ports)

# 5. Stop all services
docker-compose down
```

### Option B: Run a Single Service

```bash
# Clone individual service
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics-service
cd analytics-service/enhanced-api-phase5-analytics

# Install dependencies
pip install -r requirements-phase5-analytics.txt

# Run service
python routes_analytics.py

# Service runs on http://localhost:8000
```

---

## Clone Strategies

### Strategy 1: Full Repository (All 27 Services)

**Best for**: Local development, testing all services, Docker Compose

```bash
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git
cd piddy-microservices
```

**What you get**:
- All 27 services in separate `enhanced-api-phase{X}-{service}` directories
- Docker Compose configuration for local orchestration
- Service catalog and documentation
- All shared utilities and configurations

**Directory structure**:
```
piddy-microservices/
├── enhanced-api-phase1/              # User API
├── enhanced-api-phase2/              # Notifications
├── enhanced-api-phase3-auth/         # Phase 3 services
├── enhanced-api-phase3-email/
├── ... (all 27 services)
├── docker-compose.yml                # Run all services
├── SERVICE_CATALOG.md                # This file
└── DEPLOYMENT_GUIDE.md
```

### Strategy 2: Individual Service (Isolated)

**Best for**: Production deployment, CI/CD pipelines, independent service cloning

```bash
# Clone single service (only that service, no dependencies)
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics-service
cd analytics-service

# Contains only:
├── enhanced-api-phase5-analytics/
│   ├── routes_analytics.py
│   ├── Dockerfile
│   ├── requirements-phase5-analytics.txt
│   └── [service-specific files]
```

**Service list for individual cloning**:
```bash
# Phase 1
git clone -b service/user https://github.com/burchdad/piddy-microservices.git

# Phase 2
git clone -b service/notifications https://github.com/burchdad/piddy-microservices.git

# Phase 3
git clone -b service/auth https://github.com/burchdad/piddy-microservices.git
git clone -b service/email https://github.com/burchdad/piddy-microservices.git
git clone -b service/sms https://github.com/burchdad/piddy-microservices.git
git clone -b service/push https://github.com/burchdad/piddy-microservices.git
git clone -b service/gateway https://github.com/burchdad/piddy-microservices.git

# Phase 4
git clone -b service/event-bus https://github.com/burchdad/piddy-microservices.git
git clone -b service/notification-hub https://github.com/burchdad/piddy-microservices.git
git clone -b service/webhook https://github.com/burchdad/piddy-microservices.git
git clone -b service/task-queue https://github.com/burchdad/piddy-microservices.git
git clone -b service/secrets https://github.com/burchdad/piddy-microservices.git

# Phase 5
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git
git clone -b service/pipeline https://github.com/burchdad/piddy-microservices.git
git clone -b service/messaging https://github.com/burchdad/piddy-microservices.git
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git
git clone -b service/subscription https://github.com/burchdad/piddy-microservices.git

# Phase 6
git clone -b service/search https://github.com/burchdad/piddy-microservices.git
git clone -b service/crm https://github.com/burchdad/piddy-microservices.git
git clone -b service/cms https://github.com/burchdad/piddy-microservices.git
git clone -b service/storage https://github.com/burchdad/piddy-microservices.git
git clone -b service/monitoring https://github.com/burchdad/piddy-microservices.git

# Phase 7
git clone -b service/recommendation https://github.com/burchdad/piddy-microservices.git
git clone -b service/document-manager https://github.com/burchdad/piddy-microservices.git
git clone -b service/report-builder https://github.com/burchdad/piddy-microservices.git
git clone -b service/ml-inference https://github.com/burchdad/piddy-microservices.git
git clone -b service/social https://github.com/burchdad/piddy-microservices.git
```

### Strategy 3: Batch Clone Script

**Best for**: CI/CD automation, initial project setup

Create `clone-all-services.sh`:

```bash
#!/bin/bash

services=(
  # Phase 1
  "user"
  # Phase 2
  "notifications"
  # Phase 3
  "auth" "email" "sms" "push" "gateway"
  # Phase 4
  "event-bus" "notification-hub" "webhook" "task-queue" "secrets"
  # Phase 5
  "analytics" "pipeline" "messaging" "payment" "subscription"
  # Phase 6
  "search" "crm" "cms" "storage" "monitoring"
  # Phase 7
  "recommendation" "document-manager" "report-builder" "ml-inference" "social"
)

for service in "${services[@]}"; do
  echo "Cloning service/$service..."
  git clone -b service/$service https://github.com/burchdad/piddy-microservices.git piddy-$service &
done

wait
echo "All services cloned!"
```

Run it:
```bash
chmod +x clone-all-services.sh
./clone-all-services.sh
```

---

## Run Individual Service

### Method 1: Python Virtual Environment

```bash
# Clone service
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics

# Navigate to service
cd analytics/enhanced-api-phase5-analytics

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-phase5-analytics.txt

# Run service
python routes_analytics.py

# Service will be available at http://localhost:8000
```

### Method 2: Docker

```bash
# Clone service
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics

# Navigate to service
cd analytics/enhanced-api-phase5-analytics

# Build Docker image
docker build -t piddy-analytics .

# Run container
docker run -p 8111:8000 \
  -e DATABASE_URL=postgresql://user:password@localhost:5432/piddy \
  -e REDIS_URL=redis://localhost:6379 \
  piddy-analytics

# Service will be available at http://localhost:8111
```

### Method 3: Docker Compose (Single Service)

```bash
# Use the full repository
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git

# Start only Analytics service (and dependencies)
docker-compose up -d postgres redis analytics

# View logs
docker-compose logs -f analytics

# Stop
docker-compose down
```

---

## Run All Services (Docker)

### Prerequisites

- Docker & Docker Compose installed
- At least 16GB RAM (for all containers)
- Ports 5432, 6379, 9200, 8001-8125 available

### Startup

```bash
# Clone full repository
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git piddy
cd piddy

# Start all services
docker-compose up -d

# Monitor startup progress
docker-compose logs -f

# Check status
docker-compose ps
```

### Verify Services

```bash
# Wait for all containers to be healthy (2-3 minutes)

# Check a few key services
curl http://localhost:8001/health  # User API
curl http://localhost:8100/health  # Gateway
curl http://localhost:8111/health  # Analytics
curl http://localhost:8125/health  # Social
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs analytics

# Follow logs (live)
docker-compose logs -f user-api

# Last 100 lines
docker-compose logs --tail=100 payment
```

### Stop & Cleanup

```bash
# Stop all services (data persists)
docker-compose stop

# Remove containers (data persists)
docker-compose down

# Full cleanup (remove volumes/data)
docker-compose down -v
```

---

## Service Verification

### Health Checks

Every service exposes a `/health` endpoint:

```bash
#!/bin/bash

services=(
  "http://localhost:8001"  # User API
  "http://localhost:8002"  # Notifications
  "http://localhost:8003"  # Auth
  "http://localhost:8004"  # Email
  "http://localhost:8005"  # SMS
  "http://localhost:8006"  # Push
  "http://localhost:8100"  # Gateway
  "http://localhost:8106"  # Notification Hub
  "http://localhost:8107"  # Event Bus
  "http://localhost:8108"  # Webhook
  "http://localhost:8109"  # Task Queue
  "http://localhost:8110"  # Secrets
  "http://localhost:8111"  # Analytics
  "http://localhost:8112"  # Pipeline
  "http://localhost:8113"  # Messaging
  "http://localhost:8114"  # Payment
  "http://localhost:8115"  # Subscription
  "http://localhost:8116"  # Search
  "http://localhost:8117"  # CRM
  "http://localhost:8118"  # CMS
  "http://localhost:8119"  # Storage
  "http://localhost:8120"  # Monitoring
  "http://localhost:8121"  # Recommendation
  "http://localhost:8122"  # Document Manager
  "http://localhost:8123"  # Report Builder
  "http://localhost:8124"  # ML Inference
  "http://localhost:8125"  # Social
)

echo "Checking service health..."
for service in "${services[@]}"; do
  if curl -s "$service/health" > /dev/null; then
    echo "✅ $service"
  else
    echo "❌ $service"
  fi
done
```

### Database Verification

```bash
# Connect to PostgreSQL
psql -U piddy_user -d piddy_db -h localhost

# List tables
\dt

# Check users
SELECT * FROM users;

# Check Redis
redis-cli ping
redis-cli keys "*"

# Check Elasticsearch
curl http://localhost:9200/_cluster/health
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs {service-name}

# Verify port availability
lsof -i :8111  # Replace with your port

# Rebuild image
docker-compose up -d --build {service-name}
```

### Database Connection Error

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database exists
docker-compose exec postgres psql -U piddy_user -d piddy_db -c "\dt"

# Verify connection string
# Should be: postgresql://piddy_user:piddy_password@postgres:5432/piddy_db
```

### OutOfMemory Error

```bash
# Reduce number of services
docker-compose up -d user-api notifications auth analytics

# Or increase Docker memory limit
# Docker Desktop: Preferences > Resources > Memory
```

### Service Health Check Failing

```bash
# Check if service is ready
docker-compose exec {service} curl http://localhost:8000/health

# Check service logs
docker-compose logs {service}

# Give container more startup time
# Edit docker-compose.yml healthcheck.start_period
```

---

## Development Workflow

### Local Development (Single Service)

```bash
# 1. Clone service
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics
cd analytics/enhanced-api-phase5-analytics

# 2. Create venv
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements-phase5-analytics.txt

# 4. Run service
python routes_analytics.py

# 5. Make code changes

# 6. Commit & push
git add .
git commit -m "feat: Analytics enhancements"
git push origin service/analytics
```

### Multi-Service Testing

```bash
# 1. Clone full repo
git clone -b hybrid-phase-1-2 https://github.com/burchdad/piddy-microservices.git
cd piddy

# 2. Start dependent services only
docker-compose up -d postgres redis analytics payment subscription

# 3. Develop and test interactions between services

# 4. When ready, test full stack
docker-compose up -d

# 5. Run integration tests
pytest tests/

# 6. Commit to main hybrid branch
git push origin hybrid-phase-1-2
```

### Adding New Features

```bash
# 1. Pick a service to modify
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git

# 2. Create feature branch
cd analytics
git checkout -b feature/new-analytics-endpoint

# 3. Make changes
# Edit routes_analytics.py, add new endpoints

# 4. Test locally
python routes_analytics.py

# 5. Commit
git commit -m "feat: Add cohort analysis endpoint"

# 6. Push feature branch (for PR)
git push origin feature/new-analytics-endpoint

# 7. Or push to service branch directly
git push origin service/analytics
```

---

## Performance Tips

### Optimize for Local Development

```bash
# Start only services you need
docker-compose up -d postgres redis user-api auth analytics

# Or create a custom compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Optimize for Production

- Run services on Kubernetes (use provided manifests)
- Use managed PostgreSQL & Redis (AWS RDS, ElastiCache)
- Enable load balancing (Nginx, HAProxy)
- Use CDN for static assets (CloudFront, Cloudflare)
- Set up monitoring (Prometheus, Grafana)

---

## Next Steps

1. **Clone & run all services**: `docker-compose up -d`
2. **Review SERVICE_CATALOG.md** for detailed service documentation
3. **Test individual services** to verify functionality
4. **Read API docs** for each service (in their route files)
5. **Deploy to production** using provided Dockerfiles & configurations

---

## Support

- **Repository**: https://github.com/burchdad/piddy-microservices
- **Issues**: GitHub Issues
- **Documentation**: SERVICE_CATALOG.md, this file
- **Examples**: See individual service `routes_*.py` files

---

**Status**: ✅ All 27 services ready for deployment  
**Last Updated**: March 14, 2026  
**Total Services**: 27 | **Total LOC**: 20,000+
