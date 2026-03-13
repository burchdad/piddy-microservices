"""
Rate Limiting Configuration

Using slowapi for FastAPI rate limiting with Redis backend support.
Prevents brute force attacks on auth endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],  # Global default
    storage_uri=None,  # Use in-memory storage (use Redis for production)
)


class RateLimitConfig:
    """Rate limiting strategy configuration."""
    
    # Auth endpoints (strict)
    LOGIN_LIMIT = "5 per minute"  # Prevent brute force
    REGISTER_LIMIT = "3 per hour"  # Prevent spam registration
    PASSWORD_RESET_LIMIT = "3 per hour"
    TOKEN_REFRESH_LIMIT = "10 per minute"
    
    # API endpoints (moderate)
    READ_LIMIT = "100 per minute"
    WRITE_LIMIT = "50 per minute"
    DELETE_LIMIT = "10 per minute"
    
    # Admin endpoints
    ADMIN_LIMIT = "1000 per minute"


def setup_rate_limiting(app):
    """
    Setup rate limiting on a FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return {
        "error": "rate_limit_exceeded",
        "message": f"Rate limit exceeded: {exc.detail}",
        "status_code": 429
    }
