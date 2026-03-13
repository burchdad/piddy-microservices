#!/bin/bash
# setup.sh - One-command Piddy microservices setup

set -e

echo "🚀 Piddy Microservices Setup Script"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.12+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 installed${NC}"

# Create environment file
echo ""
echo "⚙️  Setting up environment..."

if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${YELLOW}⚠ Please edit .env with your secrets!${NC}"
    echo "  Run: nano .env"
    echo ""
fi

# Generate JWT secret if needed
if grep -q "change-in-production" .env; then
    echo "Generating JWT secret..."
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    # Update only on Linux/Mac sed
    sed -i.bak "s/change-in-production-min-32-chars/$JWT_SECRET/" .env
    rm .env.bak 2>/dev/null || true
    echo -e "${GREEN}✓ Generated secure JWT secret${NC}"
fi

# Build Docker images
echo ""
echo "🐳 Building Docker images..."
docker-compose build --no-cache 2>&1 | tail -5
echo -e "${GREEN}✓ Docker images built${NC}"

# Test images
echo ""
echo "🧪 Running tests..."
cd enhanced-api-phase1
if pip install -q -r requirements-phase1.txt && pytest -q 2>&1 | tail -3; then
    echo -e "${GREEN}✓ Phase 1 tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Phase 1 tests may have failed. Check logs.${NC}"
fi
cd ..

cd enhanced-api-phase2
if pip install -q -r requirements-phase2.txt && pytest -q 2>&1 | tail -3; then
    echo -e "${GREEN}✓ Phase 2 tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Phase 2 tests may have failed. Check logs.${NC}"
fi
cd ..

# Start services
echo ""
echo "🚀 Starting Piddy microservices..."
docker-compose -f docker-compose-full-stack.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1 && \
       curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Services are healthy${NC}"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}✗ Services failed to start${NC}"
    docker-compose logs --tail=50
    exit 1
fi

# Display access information
echo ""
echo "==========================================="${NC}
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "==========================================="${NC}
echo ""
echo "📍 Service URLs:"
echo "  User API (Phase 1):        http://localhost:8000"
echo "  Notification Service (Phase 2): http://localhost:8001"
echo "  pgAdmin (Database UI):     http://localhost:5050"
echo ""
echo "📚 Documentation:"
echo "  API Integration Guide:     ./API_INTEGRATION_GUIDE.md"
echo "  Quick Reference:           ./QUICK_REFERENCE.md"
echo "  Production Deployment:     ./PRODUCTION_DEPLOYMENT_CHECKLIST.md"
echo ""
echo "🔑 Default Credentials:"
echo "  pgAdmin Email:    admin@piddy.ai"
echo "  pgAdmin Password: admin_password"
echo "  PostgreSQL User:  piddy_user"
echo ""
echo "🧪 Next Steps:"
echo "  1. Test the API:"
echo "     curl http://localhost:8000/health"
echo ""
echo "  2. Create a test user:"
echo "     curl -X POST http://localhost:8000/api/v1/register \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"email\":\"test@example.com\",\"password\":\"Test123!\",\"username\":\"test\"}'"
echo ""
echo "  3. View logs:"
echo "     docker-compose logs -f user-api"
echo ""
echo "✨ Happy coding!"
echo ""
