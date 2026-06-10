"""
Redis client for caching and rate limiting
"""
from upstash_redis import Redis
from config import get_settings
from loguru import logger

settings = get_settings()

_redis_client = None


def get_redis_client() -> Redis:
    """Get singleton Redis client"""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = Redis(
            url=settings.upstash_redis_url,
            token=settings.upstash_redis_token
        )
    
    return _redis_client


class CacheManager:
    """Redis-based cache manager"""
    
    def __init__(self):
        self.redis = get_redis_client()
    
    def get(self, key: str):
        """Get cached value"""
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl_seconds: int = 3600):
        """Set cached value with TTL"""
        try:
            self.redis.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """Delete cached value"""
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")


class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self):
        self.redis = get_redis_client()
    
    def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if rate limit is exceeded
        
        Returns True if within limit, False if exceeded
        """
        try:
            current = self.redis.get(key)
            
            if current is None:
                # First request in window
                self.redis.setex(key, window_seconds, "1")
                return True
            
            count = int(current)
            
            if count >= limit:
                return False
            
            # Increment counter
            self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Fail open
