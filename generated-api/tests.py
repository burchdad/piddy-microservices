"""
User Management API - Comprehensive Test Suite

Tests for all API endpoints with various scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime


class TestUserRegistration:
    """Tests for user registration endpoint."""
    
    def test_register_valid_user(self, client):
        """Test successful user registration."""
        response = client.post("/api/v1/users/register", json={
            "email": "john@example.com",
            "full_name": "John Doe",
            "password": "SecurePass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "john@example.com"
        assert data["role"] == "user"
        assert "id" in data
    
    def test_register_duplicate_email(self, client, registered_user):
        """Test registration fails with duplicate email."""
        response = client.post("/api/v1/users/register", json={
            "email": registered_user["email"],
            "full_name": "Jane Doe",
            "password": "AnotherPass123"
        })
        assert response.status_code == 409
    
    def test_register_weak_password(self, client):
        """Test registration fails with weak password."""
        response = client.post("/api/v1/users/register", json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "weak"
        })
        assert response.status_code == 422
    
    def test_register_invalid_email(self, client):
        """Test registration fails with invalid email."""
        response = client.post("/api/v1/users/register", json={
            "email": "not-an-email",
            "full_name": "Test User",
            "password": "ValidPass123"
        })
        assert response.status_code == 422


class TestAuthentication:
    """Tests for authentication and token management."""
    
    def test_login_success(self, client, registered_user):
        """Test successful login."""
        response = client.post("/api/v1/users/login", json={
            "email": registered_user["email"],
            "password": "TestPass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_email(self, client):
        """Test login fails with invalid email."""
        response = client.post("/api/v1/users/login", json={
            "email": "nonexistent@example.com",
            "password": "Password123"
        })
        assert response.status_code == 401
    
    def test_login_wrong_password(self, client, registered_user):
        """Test login fails with wrong password."""
        response = client.post("/api/v1/users/login", json={
            "email": registered_user["email"],
            "password": "WrongPass123"
        })
        assert response.status_code == 401
    
    def test_refresh_token(self, client, logged_in_user):
        """Test token refresh."""
        response = client.post("/api/v1/users/refresh", json={
            "refresh_token": logged_in_user["refresh_token"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestUserProfile:
    """Tests for user profile endpoints."""
    
    def test_get_current_user(self, client, logged_in_user):
        """Test getting current user profile."""
        headers = {"Authorization": f"Bearer {logged_in_user['access_token']}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == logged_in_user["email"]
    
    def test_get_user_by_id(self, client, logged_in_user, registered_user):
        """Test getting user by ID."""
        headers = {"Authorization": f"Bearer {logged_in_user['access_token']}"}
        response = client.get(f"/api/v1/users/{registered_user['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]
    
    def test_get_nonexistent_user(self, client, logged_in_user):
        """Test getting nonexistent user returns 404."""
        headers = {"Authorization": f"Bearer {logged_in_user['access_token']}"}
        response = client.get("/api/v1/users/nonexistent-id", headers=headers)
        assert response.status_code == 404
    
    def test_update_own_profile(self, client, logged_in_user):
        """Test updating own profile."""
        headers = {"Authorization": f"Bearer {logged_in_user['access_token']}"}
        response = client.put(
            f"/api/v1/users/{logged_in_user['user_id']}",
            json={"full_name": "Updated Name"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"


class TestRBAC:
    """Tests for Role-Based Access Control."""
    
    def test_admin_only_endpoint(self, client, logged_in_user):
        """Test non-admin cannot access admin endpoint."""
        headers = {"Authorization": f"Bearer {logged_in_user['access_token']}"}
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403
    
    def test_list_users_as_admin(self, client, admin_user):
        """Test admin can list all users."""
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_pagination(self, client, admin_user):
        """Test pagination parameters work."""
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        response = client.get("/api/v1/users?skip=0&limit=5", headers=headers)
        assert response.status_code == 200
    
    def test_invalid_limit(self, client, admin_user):
        """Test invalid limit parameter."""
        headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
        response = client.get("/api/v1/users?limit=200", headers=headers)
        assert response.status_code == 422


class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_missing_auth_token(self, client):
        """Test endpoint without auth token returns 403."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403
    
    def test_invalid_auth_token(self, client):
        """Test invalid token format."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    def test_expired_token(self, client, expired_token):
        """Test expired token is rejected."""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401


# Fixtures for tests
@pytest.fixture
def client():
    """FastAPI test client."""
    # Implementation would import and create FastAPI test client
    pass


@pytest.fixture
def registered_user(client):
    """Create a registered user for testing."""
    response = client.post("/api/v1/users/register", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPass123"
    })
    return response.json()


@pytest.fixture
def logged_in_user(client, registered_user):
    """Create and log in a user."""
    response = client.post("/api/v1/users/login", json={
        "email": registered_user["email"],
        "password": "TestPass123"
    })
    tokens = response.json()
    return {**registered_user, **tokens, "user_id": registered_user["id"]}


@pytest.fixture
def admin_user(client):
    """Create an admin user."""
    # In production, would create via admin interface
    pass
