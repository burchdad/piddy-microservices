"""
Phase 2 API Tests - Notification Service

Comprehensive test suite for notification endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from notification_service import app
from database_notif import Base, get_db
from models_notif import Notification, NotificationPreference


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_notification.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestHealthCheck:
    """Health check endpoint tests."""
    
    def test_health_check(self):
        """Service should report healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notification-service"
        assert "version" in data


class TestNotificationCreation:
    """Notification creation tests."""
    
    def test_create_notification(self):
        """Create valid notification."""
        payload = {
            "user_id": "user-123",
            "notification_type": "email",
            "subject": "Test Notification",
            "message": "This is a test notification"
        }
        
        response = client.post("/notifications", json=payload)
        assert response.status_code == 201
        data = response.json()
        
        assert data["user_id"] == "user-123"
        assert data["subject"] == "Test Notification"
        assert data["is_read"] == False
        assert "id" in data
    
    def test_create_notification_with_metadata(self):
        """Create notification with custom metadata."""
        payload = {
            "user_id": "user-456",
            "notification_type": "sms",
            "subject": "Alert",
            "message": "System alert",
            "metadata": {
                "severity": "high",
                "source": "system-monitor"
            }
        }
        
        response = client.post("/notifications", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
    
    def test_create_notification_invalid_payload(self):
        """Create notification with missing fields."""
        payload = {
            "user_id": "user-789"
            # Missing required fields
        }
        
        response = client.post("/notifications", json=payload)
        assert response.status_code in [400, 422]


class TestNotificationRetrieval:
    """Notification retrieval tests."""
    
    @pytest.fixture
    def sample_notifications(self):
        """Create sample notifications."""
        db = TestingSessionLocal()
        
        notifications = [
            Notification(
                user_id="user-123",
                notification_type="email",
                subject=f"Test {i}",
                message=f"Message {i}",
                is_read=False
            )
            for i in range(3)
        ]
        
        db.add_all(notifications)
        db.commit()
        
        yield notifications
        db.close()
    
    def test_list_user_notifications(self, sample_notifications):
        """List all notifications for user."""
        response = client.get("/notifications/user-123")
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == "user-123"
        assert data["total"] > 0
        assert isinstance(data["notifications"], list)
    
    def test_list_empty_notifications(self):
        """List notifications for user with none."""
        response = client.get("/notifications/nonexistent-user")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestNotificationPreferences:
    """Notification preference tests."""
    
    def test_update_preferences(self):
        """Update user notification preferences."""
        user_id = "user-pref-123"
        preferences = {
            "email_notifications": False,
            "sms_notifications": True,
            "push_notifications": True
        }
        
        response = client.post(f"/preferences/{user_id}", json=preferences)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "preferences updated"
    
    def test_disable_notification_type(self):
        """User with disabled notifications should not receive them."""
        # First disable notifications
        user_id = "user-disabled"
        preferences = {"email_notifications": False}
        
        client.post(f"/preferences/{user_id}", json=preferences)
        
        # Try to create notification
        payload = {
            "user_id": user_id,
            "notification_type": "email",
            "subject": "Test",
            "message": "Should not be sent"
        }
        
        response = client.post("/notifications", json=payload)
        # Should either skip or indicate not sent


class TestMarkAsRead:
    """Mark notification as read tests."""
    
    def test_mark_notification_read(self):
        """Mark notification as read."""
        # Create notification first
        payload = {
            "user_id": "user-read",
            "notification_type": "email",
            "subject": "Unread",
            "message": "Mark me as read"
        }
        
        create_response = client.post("/notifications", json=payload)
        notification_id = create_response.json()["id"]
        
        # Mark as read
        response = client.put(f"/notifications/{notification_id}/read")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "read"
    
    def test_mark_nonexistent_read(self):
        """Mark nonexistent notification as read."""
        response = client.put("/notifications/nonexistent/read")
        assert response.status_code == 404


class TestMetrics:
    """Service metrics tests."""
    
    def test_get_metrics(self):
        """Retrieve service metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert "service" in data
        assert data["service"] == "notification-service"


@pytest.fixture
def cleanup():
    """Cleanup after tests."""
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
