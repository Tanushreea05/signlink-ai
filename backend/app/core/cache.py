"""
Redis cache configuration and utilities.

Provides caching functionality for API responses and session management.
"""

import json
from typing import Any, Optional
from redis import asyncio as aioredis

from app.core.config import settings


class RedisCache:
    """
    Async Redis cache client wrapper.
    
    Provides convenient methods for caching with automatic serialization.
    """
    
    def __init__(self, url: str):
        """
        Initialize Redis client.
        
        Args:
            url: Redis connection URL
        """
        self.redis = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            # Log error but don't fail
            print(f"Redis GET error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            print(f"Redis INCREMENT error: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")
            return False
    
    async def ping(self) -> bool:
        """
        Ping Redis server to check connection.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis CLEAR_PATTERN error: {e}")
            return 0


# Global Redis client instance
redis_client = RedisCache(settings.REDIS_URL)


def cache_key(*args: str) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        *args: Key components
        
    Returns:
        Cache key string
        
    Example:
        key = cache_key("user", user_id, "profile")
        # Returns: "user:123:profile"
    """
    return ":".join(str(arg) for arg in args)
