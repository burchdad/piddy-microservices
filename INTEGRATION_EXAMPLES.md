# Piddy Service Integration - Practical Examples

**Real-world usage scenarios for discovering and integrating Piddy microservices into projects**

---

## Example 1: Piddy Building a SaaS Platform

**Scenario**: Piddy needs to build a SaaS application

**Step 1: Identify Services Needed**
```
✓ User management → service/user
✓ Authentication → service/auth
✓ Email notifications → service/email
✓ Payment processing → service/payment
✓ SaaS subscriptions → service/subscription
✓ Analytics & metrics → service/analytics
✓ File storage → service/storage
```

**Step 2: Clone All Services Programmatically**
```python
# In Piddy's code generation module
from piddy_clone_manager import PiddyServiceManager

manager = PiddyServiceManager("./src/services")

services = [
    "user", "auth", "email", "payment", 
    "subscription", "analytics", "storage"
]

manager.clone_services(services)
manager.create_integration_module()
manager.create_requirements_file()
```

**Step 3: Integrate into Application**
```python
# src/main.py
from fastapi import FastAPI
from src.services.integrate import integrate_services

app = FastAPI()
integrate_services(app, prefix="/api")

# Result: All 7 services mounted and ready!
# Endpoints available:
#   /api/user/*
#   /api/auth/*
#   /api/email/*
#   /api/payment/*
#   /api/subscription/*
#   /api/analytics/*
#   /api/storage/*
```

**Step 4: Deploy Locally**
```bash
# Start everything
docker-compose up -d

# All services running + PostgreSQL + Redis
curl http://localhost:8001/health  # User service
curl http://localhost:8003/health  # Auth service
curl http://localhost:8114/health  # Payment service
```

---

## Example 2: Piddy Adding Analytics to Existing Project

**Scenario**: Piddy is enhancing an existing codebase with analytics

**Current Project Structure**
```
my-app/
├── main.py
├── models/
├── routes/
└── services/
```

**Step 1: Just Clone Analytics**
```bash
cd my-app/services
git clone -b service/analytics https://github.com/burchdad/piddy-microservices.git analytics
```

**Step 2: Mount into Existing App**
```python
# my-app/main.py
from fastapi import FastAPI
from services.analytics.enhanced-api-phase5-analytics.routes_analytics import app as analytics_app

app = FastAPI()

# Add analytics routes to existing app
app.include_router(
    analytics_app.router,
    prefix="/api/analytics",
    tags=["analytics"]
)

# Other existing routes...
```

**Step 3: Use Analytics Service**
```python
# In your existing code, now you can:
# POST /api/analytics/events/ingest - Send events
# GET /api/analytics/metrics/query - Get metrics
# POST /api/analytics/dashboards - Create dashboards
# GET /api/analytics/cohorts - User cohorts
```

---

## Example 3: Piddy Building Multi-Service Integration

**Scenario**: Piddy needs to coordinate between multiple services

**Bash Script Approach**
```bash
#!/bin/bash
# setup-my-platform.sh

# Clone multiple services
./clone-and-integrate-services.sh \
  ./services \
  user auth email payment subscription analytics

# Install dependencies
pip install -r services/requirements-combined.txt

# Deploy
docker-compose -f services/docker-compose.yml up -d

echo "Platform ready at http://localhost:8000"
```

**Python Approach**
```python
#!/usr/bin/env python3
from piddy_clone_manager import PiddyServiceManager

# Setup manager
manager = PiddyServiceManager("./services")

# Clone services
services = ["user", "auth", "payment", "analytics"]
manager.clone_services(services)

# Generate helpers
manager.create_integration_module()
manager.create_requirements_file()
manager.create_docker_compose()

# Summary
manager.print_summary()
```

---

## Example 4: Piddy Discovering the Right Service

**Scenario**: Piddy needs to send SMS notifications but doesn't remember which service

**Using the Lookup**

```python
# Check SERVICE_INTEGRATION_GUIDE.md for "SMS":
# → Found: service/sms
# → Sends SMS via Twilio or AWS SNS
# → Available at port 8005

# Clone it
git clone -b service/sms https://github.com/burchdad/piddy-microservices.git

# Check the routes_sms.py to see available endpoints
# POST /send - Send SMS
# GET /templates - SMS templates
# GET /logs - SMS history
```

---

## Example 5: Piddy Building with Service Dependencies

**Scenario**: Piddy needs services that work together (Payment + Subscription + Analytics)

**Orchestration**
```python
# services/integrate.py (auto-generated)

from payment.routes_payment import app as payment_app
from subscription.routes_subscription import app as subscription_app
from analytics.routes_analytics import app as analytics_app

def integrate_services(app):
    """Mount payment services"""
    app.include_router(payment_app.router, prefix="/api/payment")
    app.include_router(subscription_app.router, prefix="/api/subscription")
    app.include_router(analytics_app.router, prefix="/api/analytics")
    
    # All three services share same PostgreSQL & Redis
    # Payment → emits events → Event Bus → Analytics ingests metrics
    # Subscription → tracks usage → Analytics tracks consumption
```

**Integration Flow**
```
App Layer:
  ├─ /api/payment/*       → Payment Service
  ├─ /api/subscription/*  → Subscription Service
  └─ /api/analytics/*     → Analytics Service

Shared Infrastructure:
  ├─ PostgreSQL (shared database)
  ├─ Redis (shared cache)
  └─ Event Bus (optional, for async communication)
```

---

## Example 6: Piddy Deploying a Single Service to Production

**Scenario**: Production deployment of just the Payment service

**Step 1: Clone Individual Service**
```bash
git clone -b service/payment https://github.com/burchdad/piddy-microservices.git
cd payment-service/enhanced-api-phase5-payment
```

**Step 2: Build Docker Image**
```bash
docker build -t payment-service:v1 .
docker tag payment-service:v1 myregistry.azurecr.io/payment:v1
docker push myregistry.azurecr.io/payment:v1
```

**Step 3: Deploy to Kubernetes**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: payment
        image: myregistry.azurecr.io/payment:v1
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: payment-url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
```

**Step 4: Service URLs**
```
Production:
  https://api.myapp.com/payment/*
  - Stripe webhook receiver
  - Transaction processing
  - Invoice generation
```

---

## Example 7: Piddy Creating a Custom Integration

**Scenario**: Piddy needs to integrate Payment + CRM services for customer billing

**Source Structure**
```
my-project/
├── services/
│   ├── payment/          # Cloned from service/payment
│   ├── crm/              # Cloned from service/crm
│   └── custom/
│       └── billing_orchestrator.py  # Piddy's custom code
├── docker-compose.yml
└── main.py
```

**Custom Orchestrator Code**
```python
# services/custom/billing_orchestrator.py

from payment.enhanced-api-phase5-payment.routes_payment import app as payment_app
from crm.enhanced-api-phase6-crm.routes_crm import app as crm_app

class BillingOrchestrator:
    """Coordinate between Payment and CRM services"""
    
    def process_subscription_payment(self, customer_id: str, amount: float):
        """
        1. Get customer from CRM
        2. Process payment via Payment service
        3. Update customer in CRM with payment status
        """
        # Get customer from CRM
        customer = crm_app.get_customer(customer_id)
        
        # Create payment
        payment = payment_app.create_payment(
            customer_email=customer.email,
            amount=amount
        )
        
        # Update CRM with payment info
        crm_app.add_interaction(
            customer_id,
            type="payment",
            data={"payment_id": payment.id, "amount": amount}
        )
        
        return payment
```

---

## Example 8: Piddy on Autopilot - Full Workflow

**Scenario**: Piddy autonomously builds a complete platform

```python
import os
from pathlib import Path
from piddy_clone_manager import PiddyServiceManager

class PiddyPlatformBuilder:
    """Autonomous platform builder using Piddy services"""
    
    def __init__(self, platform_name: str):
        self.platform_dir = Path(platform_name)
        self.platform_dir.mkdir(exist_ok=True)
        self.manager = PiddyServiceManager(self.platform_dir / "services")
    
    def build_ecommerce_platform(self):
        """Build complete e-commerce application"""
        
        print("🤖 Piddy building e-commerce platform...")
        
        # Step 1: Identify required services
        required_services = [
            "user",           # User management
            "auth",           # Authentication
            "payment",        # Payment processing
            "analytics",      # Sales analytics
            "crm",            # Customer management
            "storage",        # Product images
            "messaging",      # Order notifications
            "search",         # Product search
            "recommendation"  # Recommendations
        ]
        
        # Step 2: Clone all services
        print(f"📦 Cloning {len(required_services)} services...")
        self.manager.clone_services(required_services)
        
        # Step 3: Generate integration files
        print("⚙️  Generating integration files...")
        self.manager.create_integration_module()
        self.manager.create_requirements_file()
        self.manager.create_docker_compose()
        
        # Step 4: Create main application
        print("🏗️  Creating main application...")
        self._create_main_app()
        
        # Step 5: Create documentation
        print("📚 Creating documentation...")
        self._create_readmes()
        
        # Done!
        print("✅ Platform ready to launch!")
        self.manager.print_summary()
    
    def _create_main_app(self):
        """Generate main.py that integrates all services"""
        main_py = self.platform_dir / "main.py"
        
        main_py.write_text(f'''
from fastapi import FastAPI
from services.integrate import integrate_services

app = FastAPI(
    title="E-Commerce Platform",
    description="Built with Piddy microservices"
)

# Mount all microservices
integrate_services(app, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''')
    
    def _create_readmes(self):
        """Generate project documentation"""
        readme = self.platform_dir / "README.md"
        readme.write_text(f'''# E-Commerce Platform

Built with Piddy Microservices

## Services

- **User**: User management and profiles
- **Auth**: JWT authentication
- **Payment**: Stripe integration
- **Analytics**: Sales metrics and reports
- **CRM**: Customer relationship management
- **Storage**: Product images and files
- **Messaging**: Order notifications
- **Search**: Full-text product search
- **Recommendation**: AI product recommendations

## Getting Started

```bash
# Install dependencies
pip install -r services/requirements-combined.txt

# Start all services
docker-compose up -d

# Run application
python main.py
```

## Available Endpoints

- POST /api/user/register
- POST /api/auth/login
- POST /api/payment/create
- GET /api/analytics/metrics
- And more!
''')

# Piddy runs this automatically
if __name__ == "__main__":
    builder = PiddyPlatformBuilder("my-ecommerce")
    builder.build_ecommerce_platform()
```

**Output**:
```
🤖 Piddy building e-commerce platform...
📦 Cloning 9 services...
  ✓ user
  ✓ auth
  ✓ payment
  [...]
⚙️  Generating integration files...
  ✓ Created integration module
  ✓ Created combined requirements
  ✓ Created docker-compose.yml
🏗️  Creating main application...
📚 Creating documentation...
✅ Platform ready to launch!
```

---

## Key Takeaway

**Piddy (or any developer) can now:**

1. **Discover** - Look up what service is needed by function
2. **Clone** - Git clone or use automation tools
3. **Integrate** - Automatic integration module generation
4. **Deploy** - Docker Compose or individual service deployment
5. **Scale** - Each service runs independently

**All 27 services are production-ready and instantly available.**

No rebuilding, no recreating - just clone, integrate, and deploy! 🚀
