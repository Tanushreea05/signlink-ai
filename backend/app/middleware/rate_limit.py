"""
Rate limiting middleware.

Implements token bucket algorithm for API rate limiting.
"""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import redis_client, cache_key
from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    
    Implements token bucket algorithm with per-user rate limits.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Get user identifier (IP or user ID from token)
        user_id = await self._get_user_identifier(request)
        
        # Check rate limit
        is_allowed, retry_after = await self._check_rate_limit(user_id)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(
            await self._get_remaining_requests(user_id)
        )
        
        return response
    
    async def _get_user_identifier(self, request: Request) -> str:
        """
        Get user identifier for rate limiting.
        
        Args:
            request: Incoming request
            
        Returns:
            User identifier (user ID or IP address)
        """
        # Try to get user ID from token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                return f"user:{payload.get('sub')}"
            except Exception:
                pass
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        key = cache_key("rate_limit", user_id)
        current_time = int(time.time())
        window_start = current_time - 60  # 1 minute window
        
        try:
            # Get request count in current window
            count = await redis_client.get(key)
            
            if count is None:
                # First request in window
                await redis_client.set(key, 1, ttl=60)
                return True, 0
            
            count = int(count)
            
            if count >= settings.RATE_LIMIT_PER_MINUTE:
                # Rate limit exceeded
                ttl = await redis_client.redis.ttl(key)
                return False, max(ttl, 1)
            
            # Increment counter
            await redis_client.increment(key)
            return True, 0
        
        except Exception as e:
            # If Redis fails, allow the request
            print(f"Rate limit check failed: {e}")
            return True, 0
    
    async def _get_remaining_requests(self, user_id: str) -> int:
        """
        Get remaining requests in current window.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of remaining requests
        """
        key = cache_key("rate_limit", user_id)
        
        try:
            count = await redis_client.get(key)
            if count is None:
                return settings.RATE_LIMIT_PER_MINUTE
            
            remaining = settings.RATE_LIMIT_PER_MINUTE - int(count)
            return max(remaining, 0)
        
        except Exception:
            return settings.RATE_LIMIT_PER_MINUTE
