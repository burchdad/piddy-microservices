"""
Background Task Queue Service

Manages async notification delivery via Celery/Redis.
"""

import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from enum import Enum as PyEnum

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class QueueName(PyEnum):
    """Queue names."""
    NOTIFICATIONS = "queue:notifications"
    EMAILS = "queue:emails"
    SMS = "queue:sms"
    WEBHOOKS = "queue:webhooks"
    FAILED = "queue:failed"


class QueueService:
    """Background task queue using Redis."""
    
    def __init__(self, redis_conn=None):
        self.redis = redis_conn or redis_client
        self.failed_queue = QueueName.FAILED.value
    
    async def queue_notification(
        self,
        notification_id: str,
        user_id: str,
        subject: str,
        message: str,
        delay: int = 0,
        priority: str = "normal"
    ) -> bool:
        """Queue a notification for async delivery."""
        
        task = {
            "notification_id": notification_id,
            "user_id": user_id,
            "subject": subject,
            "message": message,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        try:
            queue_name = QueueName.NOTIFICATIONS.value
            
            if delay > 0:
                # Delayed delivery
                score = (datetime.utcnow() + timedelta(seconds=delay)).timestamp()
                self.redis.zadd(f"{queue_name}:delayed", {json.dumps(task): score})
            else:
                # Immediate delivery
                self.redis.rpush(queue_name, json.dumps(task))
            
            # Track task
            self.redis.hset("tasks:active", notification_id, queue_name)
            
            return True
        except Exception as e:
            print(f"✗ Failed to queue notification: {e}")
            return False
    
    async def dequeue_notifications(self, count: int = 10) -> list:
        """Dequeue tasks for processing."""
        tasks = []
        
        try:
            queue_name = QueueName.NOTIFICATIONS.value
            
            while len(tasks) < count:
                task_json = self.redis.lpop(queue_name)
                if not task_json:
                    break
                
                task = json.loads(task_json)
                tasks.append(task)
            
            return tasks
        except Exception as e:
            print(f"✗ Failed to dequeue tasks: {e}")
            return []
    
    async def mark_task_complete(self, notification_id: str) -> bool:
        """Mark task as completed."""
        try:
            self.redis.hdel("tasks:active", notification_id)
            self.redis.hset("tasks:completed", notification_id, datetime.utcnow().isoformat())
            return True
        except Exception as e:
            print(f"✗ Failed to mark task complete: {e}")
            return False
    
    async def mark_task_failed(self, notification_id: str, error: str, retry: bool = True) -> bool:
        """Mark task as failed."""
        try:
            self.redis.hdel("tasks:active", notification_id)
            
            failure_info = {
                "notification_id": notification_id,
                "error": error,
                "failed_at": datetime.utcnow().isoformat(),
                "should_retry": retry
            }
            
            self.redis.rpush(self.failed_queue, json.dumps(failure_info))
            return True
        except Exception as e:
            print(f"✗ Failed to mark task failed: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {
            "notifications_queued": self.redis.llen(QueueName.NOTIFICATIONS.value),
            "tasks_active": self.redis.hlen("tasks:active"),
            "tasks_completed": self.redis.hlen("tasks:completed"),
            "failed_tasks": self.redis.llen(self.failed_queue),
            "timestamp": datetime.utcnow().isoformat()
        }
        return stats


# Global instance
queue_service = QueueService(redis_client)


async def queue_notification(
    notification_id: str,
    user_id: str,
    subject: str,
    message: str
) -> bool:
    """Convenience function to queue notification."""
    return await queue_service.queue_notification(
        notification_id,
        user_id,
        subject,
        message
    )


async def dequeue_and_process():
    """Worker function to process queued notifications."""
    while True:
        try:
            tasks = await queue_service.dequeue_notifications(count=10)
            
            for task in tasks:
                try:
                    # Process notification (send email, SMS, etc)
                    # This would integrate with email_service, sms_service, etc
                    print(f"Processing: {task['notification_id']}")
                    
                    # On success:
                    await queue_service.mark_task_complete(task['notification_id'])
                    
                except Exception as e:
                    print(f"✗ Task failed: {e}")
                    await queue_service.mark_task_failed(
                        task['notification_id'],
                        str(e)
                    )
            
            # Sleep before checking again
            await asyncio.sleep(5)
        
        except Exception as e:
            print(f"✗ Worker error: {e}")
            await asyncio.sleep(10)
