"""
Rate limiting utilities for API endpoints
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.core.config import settings

# Create rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
# These can be overridden per endpoint
RATE_LIMITS = {
    "default": "100/minute",  # Default: 100 requests per minute
    "auth": "10/minute",  # Auth endpoints: 10 requests per minute
    "submissions": "30/minute",  # Submission operations: 30 per minute
    "jobs": "20/minute",  # Job operations: 20 per minute
    "stats": "60/minute",  # Statistics endpoints: 60 per minute
    "health": "200/minute",  # Health checks: 200 per minute
}


def get_rate_limit(limit_type: str = "default") -> str:
    """
    Get rate limit string for a specific endpoint type.
    
    Args:
        limit_type: Type of endpoint (default, auth, submissions, jobs, stats, health)
        
    Returns:
        Rate limit string in format "X/minute" or "X/hour"
    """
    return RATE_LIMITS.get(limit_type, RATE_LIMITS["default"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a JSON response with rate limit information.
    """
    response = _rate_limit_exceeded_handler(request, exc)
    response.headers["X-RateLimit-Limit"] = str(exc.detail.get("limit", "unknown"))
    response.headers["X-RateLimit-Remaining"] = str(exc.detail.get("remaining", 0))
    response.headers["X-RateLimit-Reset"] = str(exc.detail.get("reset", 0))
    return response
