#!/bin/bash

# clone-and-integrate-services.sh
# Automated script to clone Piddy microservices and integrate them into a project

set -e

PIDDY_REPO="https://github.com/burchdad/piddy-microservices.git"
SERVICES_DIR="${1:-.}/services"
SERVICES_TO_CLONE="${@:2}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Piddy Microservices Integration Tool${NC}"
echo "========================================"
echo ""

# Show usage if no services specified
if [ -z "$SERVICES_TO_CLONE" ]; then
  echo -e "${RED}Usage: ./clone-and-integrate-services.sh [target_dir] [service1] [service2] ...${NC}"
  echo ""
  echo "Example:"
  echo "  ./clone-and-integrate-services.sh ./src/services user auth payment analytics"
  echo ""
  echo "Available services:"
  echo "  Phase 1: user"
  echo "  Phase 2: notifications"
  echo "  Phase 3: auth email sms push gateway"
  echo "  Phase 4: event-bus notification-hub webhook task-queue secrets"
  echo "  Phase 5: analytics pipeline messaging payment subscription"
  echo "  Phase 6: search crm cms storage monitoring"
  echo "  Phase 7: recommendation document-manager report-builder ml-inference social"
  echo ""
  exit 1
fi

# Create services directory
mkdir -p "$SERVICES_DIR"
echo -e "${YELLOW}Target directory: $SERVICES_DIR${NC}"
echo ""

# Clone each service
CLONED_SERVICES=()
FAILED_SERVICES=()

for service in $SERVICES_TO_CLONE; do
  echo -e "${YELLOW}Cloning service: $service${NC}"
  
  SERVICE_DIR="$SERVICES_DIR/$service"
  
  if git clone -b "service/$service" "$PIDDY_REPO" "$SERVICE_DIR" 2>/dev/null; then
    echo -e "${GREEN}✓ Cloned: $service${NC}"
    CLONED_SERVICES+=("$service")
    
    # List what was cloned
    SERVICE_ROUTE_DIR=$(find "$SERVICE_DIR" -name "routes_*.py" | head -1 | xargs dirname)
    ROUTES_FILE=$(find "$SERVICE_DIR" -name "routes_*.py" | head -1)
    DOCKERFILE=$(find "$SERVICE_DIR" -name "Dockerfile" | head -1)
    REQUIREMENTS=$(find "$SERVICE_DIR" -name "requirements-*.txt" | head -1)
    
    echo "  • Routes: $ROUTES_FILE"
    echo "  • Dockerfile: $DOCKERFILE"
    echo "  • Requirements: $REQUIREMENTS"
    
  else
    echo -e "${RED}✗ Failed to clone: $service${NC}"
    FAILED_SERVICES+=("$service")
  fi
  echo ""
done

# Summary
echo "========================================"
echo -e "${GREEN}Cloned ${#CLONED_SERVICES[@]} service(s):${NC}"
for service in "${CLONED_SERVICES[@]}"; do
  echo "  • $service"
done

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
  echo ""
  echo -e "${RED}Failed to clone ${#FAILED_SERVICES[@]} service(s):${NC}"
  for service in "${FAILED_SERVICES[@]}"; do
    echo "  • $service"
  done
fi

# Create integration helper
if [ ${#CLONED_SERVICES[@]} -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}Creating integration helper...${NC}"
  
  INTEGRATION_FILE="$SERVICES_DIR/integrate.py"
  
  cat > "$INTEGRATION_FILE" << 'EOF'
"""
Piddy Microservices Integration Helper

Auto-generated integration script for cloned services.
Import and mount these services into your FastAPI app.
"""

import sys
import os
from pathlib import Path

# Add services to path
services_path = Path(__file__).parent
sys.path.insert(0, str(services_path))

# Import all service routes
services = {}

EOF

  # Add imports for each cloned service
  for service in "${CLONED_SERVICES[@]}"; do
    SERVICE_DIR="$SERVICES_DIR/$service"
    PHASE_DIR=$(find "$SERVICE_DIR" -type d -name "enhanced-api-phase*" | head -1)
    ROUTES_FILE=$(find "$PHASE_DIR" -name "routes_*.py" 2>/dev/null | head -1)
    
    if [ -n "$ROUTES_FILE" ]; then
      ROUTES_NAME=$(basename "$ROUTES_FILE" .py)
      PHASE_NAME=$(basename "$PHASE_DIR")
      
      cat >> "$INTEGRATION_FILE" << EOF
try:
    from ${service}/${PHASE_NAME}/${ROUTES_NAME} import app as ${service}_app
    services['${service}'] = ${service}_app
except ImportError as e:
    print(f"Warning: Could not import ${service} service: {e}")

EOF
    fi
  done
  
  cat >> "$INTEGRATION_FILE" << 'EOF'

def integrate_services(app, prefix="/api"):
    """
    Mount all cloned services to your FastAPI app.
    
    Usage:
        from fastapi import FastAPI
        from services.integrate import integrate_services
        
        app = FastAPI()
        integrate_services(app)
        
        # All service endpoints now available under /api/
    """
    for service_name, service_app in services.items():
        if hasattr(service_app, 'router'):
            app.include_router(
                service_app.router,
                prefix=f"{prefix}/{service_name}",
                tags=[service_name]
            )
        print(f"✓ Integrated {service_name} service")


if __name__ == "__main__":
    print("Piddy Microservices Integration Helper")
    print("Available services:", list(services.keys()))
    print("\nUsage:")
    print("  from integrate import integrate_services")
    print("  integrate_services(app)")
EOF

  echo -e "${GREEN}✓ Created: $INTEGRATION_FILE${NC}"
fi

# Create requirements file
if [ ${#CLONED_SERVICES[@]} -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}Creating combined requirements...${NC}"
  
  REQUIREMENTS_FILE="$SERVICES_DIR/requirements-combined.txt"
  > "$REQUIREMENTS_FILE"  # Clear file
  
  for service in "${CLONED_SERVICES[@]}"; do
    SERVICE_REQ=$(find "$SERVICES_DIR/$service" -name "requirements-*.txt" | head -1)
    if [ -f "$SERVICE_REQ" ]; then
      echo "# Requirements for $service" >> "$REQUIREMENTS_FILE"
      cat "$SERVICE_REQ" >> "$REQUIREMENTS_FILE"
      echo "" >> "$REQUIREMENTS_FILE"
    fi
  done
  
  echo -e "${GREEN}✓ Created: $REQUIREMENTS_FILE${NC}"
  
  # Remove duplicates
  sort -u "$REQUIREMENTS_FILE" -o "$REQUIREMENTS_FILE"
  echo -e "${GREEN}✓ Removed duplicate dependencies${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Integration complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. pip install -r services/requirements-combined.txt"
echo "  2. from services.integrate import integrate_services"
echo "  3. integrate_services(app)"
echo ""
echo "Your services are ready to use!"
