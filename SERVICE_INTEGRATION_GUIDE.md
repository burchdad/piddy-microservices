# Piddy Service Integration Guide

**How to discover, clone, and integrate microservices into any project**

---

## Quick Lookup: Find the Service You Need

### Authentication & Security
- `service/user` - User management, profiles, roles
- `service/auth` - JWT, MFA, OAuth2
- `service/secrets` - Secrets management, encryption

### Communication
- `service/notifications` - Queue-based notifications
- `service/email` - SendGrid, AWS SES integration
- `service/sms` - Twilio, AWS SNS
- `service/push` - Firebase push notifications
- `service/messaging` - Real-time chat, channels

### Data & Analytics
- `service/analytics` - Event ingestion, metrics, dashboards
- `service/pipeline` - ETL/ELT, transformations
- `service/search` - Full-text search, Elasticsearch

### Business Operations
- `service/payment` - Stripe/PayPal integration
- `service/subscription` - SaaS billing, plans
- `service/crm` - Contacts, deals, pipelines
- `service/cms` - Content publishing, versioning

### Infrastructure & Observability
- `service/event-bus` - Pub/Sub messaging
- `service/webhook` - Webhook management
- `service/task-queue` - Background jobs
- `service/monitoring` - Health checks, alerts
- `service/gateway` - API gateway, routing

### Files & Storage
- `service/storage` - File upload, S3, CDN
- `service/document-manager` - OCR, versioning

### Advanced
- `service/recommendation` - ML recommendations
- `service/report-builder` - Dynamic reports
- `service/ml-inference` - Model serving, predictions
- `service/social` - Posts, follows, activity feeds

---

## Integration Workflow

### 1. Identify What You Need

**Example: Building a SaaS platform**
- Need user management → `service/user`
- Need billing → `service/payment` + `service/subscription`
- Need analytics → `service/analytics`
- Need file uploads → `service/storage`

### 2. Clone the Service

```bash
# Clone specific service
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git payment-service

# Or clone directly into your project
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git src/services/payment
```

### 3. Extract the Service Directory

```bash
# Service is in enhanced-api-phase{X}-{service}/
cd payment-service/enhanced-api-phase5-payment

# Copy to your project
cp -r . /path/to/your/project/src/services/payment/

# Or create a git subtree
git subtree add --prefix services/payment https://github.com/burchdad/piddy-microservices.git service/payment
```

### 4. Install Dependencies

```bash
cd /path/to/services/payment
pip install -r requirements-phase5-payment.txt
```

### 5. Integrate into Your Code

```python
# In your main application
from services.payment.routes_payment import app as payment_app

# Mount as sub-application
app.include_router(payment_app.router, prefix="/api/payment")

# Or use directly
from services.payment import routes_payment
payment_service = routes_payment
```

---

## Common Integration Patterns

### Pattern 1: Clone Single Service into Project

```bash
# Your project structure
my-app/
├── src/
│   ├── main.py
│   ├── services/
│   │   ├── payment/           # Cloned from service/payment
│   │   ├── analytics/         # Cloned from service/analytics
│   │   └── crm/               # Cloned from service/crm
│   └── models.py

# Clone
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git src/services/payment
```

### Pattern 2: Combine Multiple Services

```python
# src/main.py
from fastapi import FastAPI
from src.services.payment import routes_payment
from src.services.analytics import routes_analytics
from src.services.user import routes_user

app = FastAPI()

# Mount all services
app.include_router(routes_payment.app.router, tags=["payments"])
app.include_router(routes_analytics.app.router, tags=["analytics"])
app.include_router(routes_user.app.router, tags=["users"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Pattern 3: Use Service in Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: password

  redis:
    image: redis:7

  # Reuse payment service directly
  payment-service:
    build: ./services/payment/enhanced-api-phase5-payment
    ports:
      - "8114:8000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/db
      REDIS_URL: redis://redis:6379

  my-app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - payment-service
```

### Pattern 4: Create Service Package

```bash
# Create a Python package from services
my_app/
├── services_package/
│   ├── __init__.py
│   ├── payment/           # From git clone
│   ├── analytics/         # From git clone
│   └── user/              # From git clone
└── setup.py               # Makes it installable
```

Install as package in other projects:
```bash
pip install -e /path/to/my_app/services_package
```

---

## Batch Clone Script

Clone multiple services at once:

```bash
#!/bin/bash

# clone-services.sh
services=(
  "user"
  "payment"
  "analytics"
  "storage"
  "crm"
)

for service in "${services[@]}"; do
  echo "Cloning service/$service..."
  git clone -b service/$service \
    https://github.com/burchdad/piddy-microservices.git \
    services/$service &
done

wait
echo "All services cloned!"
```

Run:
```bash
chmod +x clone-services.sh
./clone-services.sh
```

---

## Update Service

If you cloned a service and it gets updated on GitHub:

**Option 1: Update via Git Subtree**
```bash
git subtree pull --prefix services/payment \
  https://github.com/burchdad/piddy-microservices.git \
  service/payment --squash
```

**Option 2: Re-clone**
```bash
rm -rf services/payment
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git services/payment
```

---

## Example: Building a Platform with Piddy Services

### Day 1: Setup Base Platform

```bash
# Create project
mkdir my-platform && cd my-platform
git init

# Clone core services
git clone -b service/user https://github.com/burchdad/piddy-microservices.git services/user
git clone -b service/auth https://github.com/burchdad/piddy-microservices.git services/auth
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git services/analytics

# Create main app
cat > main.py << 'EOF'
from fastapi import FastAPI
from services.user.enhanced-api-phase1.routes import app as user_app
from services.auth.enhanced-api-phase3-auth.routes_auth import app as auth_app

app = FastAPI()
app.include_router(user_app.router)
app.include_router(auth_app.router)
EOF

# Run
python main.py
```

### Day 2: Add Payments

```bash
# Clone payment service
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git services/payment

# Update main.py
# Add: from services.payment.enhanced-api-phase5-payment.routes_payment import app as payment_app
# Add: app.include_router(payment_app.router)

# Restart - payment endpoints now available
```

### Day 3: Add Analytics & Storage

```bash
# Clone additional services
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git services/analytics
git clone -b service/storage https://github.com/burchdad/piddy-microservices.git services/storage

# Update main.py with new routers
# Now have: users, auth, payments, analytics, storage
```

---

## Service Compatibility

All services share the same:
- **Python Version**: 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Pattern**: FastAPI routes with SQLAlchemy models

**This means they work together perfectly** - no version conflicts, consistent patterns, ready to integrate.

---

## Troubleshooting Integration

### Import Error: Module not found
```python
# Make sure service is in Python path
import sys
sys.path.insert(0, '/path/to/services/payment')
```

### Database Connection
```python
# Use environment variables
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
```

### Port Conflicts
```python
# Change port when running service directly
import uvicorn
uvicorn.run(app, port=8114)  # Not 8000
```

---

## Service API Contract

All services follow this pattern:

```python
# routes_{service}.py

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = FastAPI()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Routes
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/{resource}")
async def create_resource(data: Schema):
    # Business logic
    pass

# Easy to import and use
```

---

## Documentation per Service

Each cloned service includes:
- `routes_{service}.py` - Main code with docstrings
- `Dockerfile` - Container definition
- `requirements-phase{X}-{service}.txt` - Dependencies
- Model and schema definitions
- Full endpoint documentation in code

**In-code comments explain the API and data model for each service.**

---

## Next Steps

1. **Identify services you need** using the lookup table above
2. **Clone them**: `git clone -b service/{name} https://github.com/burchdad/piddy-microservices.git`
3. **Install dependencies**: `pip install -r requirements-*.txt`
4. **Integrate into your project**: Import routers or use as Docker services
5. **Deploy** - Each service can run independently

---

## Quick Reference: All 27 Services

```
Phase 1:  user
Phase 2:  notifications
Phase 3:  auth, email, sms, push, gateway
Phase 4:  event-bus, notification-hub, webhook, task-queue, secrets
Phase 5:  analytics, pipeline, messaging, payment, subscription
Phase 6:  search, crm, cms, storage, monitoring
Phase 7:  recommendation, document-manager, report-builder, ml-inference, social
```

Clone any with: `git clone -b service/{name} https://github.com/burchdad/piddy-microservices.git`

---

**Your microservices are now a reusable component library! Just clone what you need.**
