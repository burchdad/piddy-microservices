#!/bin/bash
# integration-tests.sh - Verify Piddy microservices are working correctly

set -e

API_URL="http://localhost:8000/api/v1"
NOTIF_URL="http://localhost:8001"
TIMESTAMP=$(date +%s)
TEST_EMAIL="test-$TIMESTAMP@example.com"
TEST_PASSWORD="TestPassword123!"
TEST_USERNAME="test_$TIMESTAMP"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🧪 Piddy Microservices Integration Tests"
echo "========================================"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test endpoints
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_code=$5
    
    echo -n "Testing $name... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" == "$expected_code" ]; then
        echo -e "${GREEN}✓ (HTTP $http_code)${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "$body"
    else
        echo -e "${RED}✗ Expected $expected_code, got $http_code${NC}"
        echo "Response: $body"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo ""
}

# ==========================================
# Phase 1: User API Tests
# ==========================================
echo "Phase 1: User API Tests"
echo "======================================"

# Test 1: Health check
test_endpoint "User API Health" "GET" "$API_URL/../health" "" "200"

# Test 2: Register user
echo -n "Testing User Registration... "
register_response=$(curl -s -X POST "$API_URL/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\",
        \"username\": \"$TEST_USERNAME\"
    }")
USER_ID=$(echo "$register_response" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"\|"//g')

if [ -n "$USER_ID" ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  User ID: $USER_ID"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $register_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    exit 1
fi
echo ""

# Test 3: Login
echo -n "Testing User Login... "
login_response=$(curl -s -X POST "$API_URL/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\"
    }")
ACCESS_TOKEN=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | head -1 | sed 's/"access_token":"\|"//g')

if [ -n "$ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  Token length: ${#ACCESS_TOKEN}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $login_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 4: Get current user
echo -n "Testing Get Current User... "
user_response=$(curl -s -X GET "$API_URL/users/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
if echo "$user_response" | grep -q "$TEST_EMAIL"; then
    echo -e "${GREEN}✓${NC}"
    echo "  Email: $TEST_EMAIL"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $user_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# ==========================================
# Phase 2: Notification Service Tests
# ==========================================
echo ""  
echo "Phase 2: Notification Service Tests"
echo "======================================"

# Test 5: Notification API Health
test_endpoint "Notification Service Health" "GET" "$NOTIF_URL/health" "" "200"

# Test 6: Create notification
echo -n "Testing Create Notification... "
notif_response=$(curl -s -X POST "$NOTIF_URL/notifications" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"notification_type\": \"email\",
        \"subject\": \"Integration Test\",
        \"message\": \"This is a test notification\"
    }")
NOTIF_ID=$(echo "$notif_response" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"\|"//g')

if [ -n "$NOTIF_ID" ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  Notification ID: $NOTIF_ID"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $notif_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 7: List user notifications
echo -n "Testing List Notifications... "
list_response=$(curl -s -X GET "$NOTIF_URL/notifications/$USER_ID")
if echo "$list_response" | grep -q "Integration Test"; then
    echo -e "${GREEN}✓${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $list_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 8: Mark as read
if [ -n "$NOTIF_ID" ]; then
    echo -n "Testing Mark as Read... "
    read_response=$(curl -s -X PUT "$NOTIF_URL/notifications/$NOTIF_ID/read")
    if echo "$read_response" | grep -q "read"; then
        echo -e "${GREEN}✓${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC}"
        echo "  Response: $read_response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo ""
fi

# Test 9: Update preferences
echo -n "Testing Update Notification Preferences... "
pref_response=$(curl -s -X POST "$NOTIF_URL/preferences/$USER_ID" \
    -H "Content-Type: application/json" \
    -d "{
        \"email_notifications\": true,
        \"sms_notifications\": false,
        \"push_notifications\": true
    }")
if echo "$pref_response" | grep -q "updated"; then
    echo -e "${GREEN}✓${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗${NC}"
    echo "  Response: $pref_response"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test 10: Service metrics
test_endpoint "Notification Service Metrics" "GET" "$NOTIF_URL/metrics" "" "200"

# ==========================================
# Results
# ==========================================
echo ""
echo "========================================"
echo "Test Results"
echo "========================================"
echo -e "${GREEN}✓ Passed: $TESTS_PASSED${NC}"
echo -e "${RED}✗ Failed: $TESTS_FAILED${NC}"
echo ""

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL))

echo "Pass Rate: $PASS_RATE% ($TESTS_PASSED/$TOTAL)"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All integration tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check the output above.${NC}"
    exit 1
fi
