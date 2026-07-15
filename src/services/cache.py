"""
Redis cache service for caching RAG responses.
"""

import hashlib
import json
from typing import Any, Dict, Optional

import redis.asyncio as redis

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

logger = LoggerAdapter(__name__)


class RedisCache:
    """
    Redis cache service for caching chat responses.

    Features:
    - Async operations
    - TTL-based expiration
    - JSON serialization
    - Cache hit/miss tracking
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: Optional[int] = None,
        enabled: bool = True,
    ) -> None:
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live in seconds
            enabled: Enable/disable caching
        """
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl or settings.redis_ttl
        self.enabled = enabled

        logger.info(
            "Initializing Redis cache",
            redis_url=self.redis_url,
            ttl=self.ttl,
            enabled=self.enabled,
        )

        self.redis: Optional[redis.Redis] = None
        self._hits = 0
        self._misses = 0

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.enabled:
            logger.info("Cache disabled, skipping connection")
            return

        try:
            self.redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.enabled = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis cache disconnected")

    async def __aenter__(self) -> "RedisCache":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def _generate_key(self, question: str, course_id: Optional[str] = None) -> str:
        """
        Generate cache key from question and course_id.

        Args:
            question: User question
            course_id: Course ID

        Returns:
            str: Cache key
        """
        key_data = f"{question}:{course_id or 'global'}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"chat:{key_hash}"

    async def get(self, question: str, course_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response.

        Args:
            question: User question
            course_id: Course ID

        Returns:
            Cached response dict or None
        """
        if not self.enabled or not self.redis:
            return None

        key = self._generate_key(question, course_id)

        try:
            cached = await self.redis.get(key)
            if cached:
                self._hits += 1
                logger.debug("Cache hit", key=key, hit_rate=self.get_hit_rate())
                return json.loads(cached)
            else:
                self._misses += 1
                logger.debug("Cache miss", key=key, hit_rate=self.get_hit_rate())
                return None
        except Exception as e:
            logger.error("Cache get failed", error=str(e), key=key)
            return None

    async def set(
        self,
        question: str,
        response: Dict[str, Any],
        course_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache response.

        Args:
            question: User question
            response: Response to cache
            course_id: Course ID
            ttl: TTL in seconds (default: from settings)
        """
        if not self.enabled or not self.redis:
            return

        key = self._generate_key(question, course_id)
        ttl = ttl or self.ttl

        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(response, ensure_ascii=False),
            )
            logger.debug("Cached response", key=key, ttl=ttl)
        except Exception as e:
            logger.error("Cache set failed", error=str(e), key=key)

    async def delete(self, question: str, course_id: Optional[str] = None) -> None:
        """
        Delete cached response.

        Args:
            question: User question
            course_id: Course ID
        """
        if not self.enabled or not self.redis:
            return

        key = self._generate_key(question, course_id)

        try:
            await self.redis.delete(key)
            logger.debug("Deleted cache entry", key=key)
        except Exception as e:
            logger.error("Cache delete failed", error=str(e), key=key)

    async def clear_course(self, course_id: str) -> int:
        """
        Clear all cached responses for a course.

        Args:
            course_id: Course ID

        Returns:
            int: Number of keys deleted
        """
        if not self.enabled or not self.redis:
            return 0

        pattern = f"chat:*:{course_id}:*"

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info("Cleared course cache", course_id=course_id, deleted=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("Failed to clear course cache", course_id=course_id, error=str(e))
            return 0

    async def clear_all(self) -> None:
        """Clear all cached responses."""
        if not self.enabled or not self.redis:
            return

        try:
            await self.redis.flushdb()
            logger.info("Cleared all cache")
            self._hits = 0
            self._misses = 0
        except Exception as e:
            logger.error("Failed to clear cache", error=str(e))

    def get_hit_rate(self) -> float:
        """
        Get cache hit rate.

        Returns:
            float: Hit rate (0.0 to 1.0)
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self._hits + self._misses,
        }


# Global cache instance
_cache: Optional[RedisCache] = None


async def get_redis_cache() -> RedisCache:
    """
    Get global Redis cache instance (singleton).

    Returns:
        RedisCache: Redis cache instance
    """
    global _cache
    if _cache is None:
        _cache = RedisCache()
        await _cache.connect()
    return _cache


async def close_redis_cache() -> None:
    """Close global Redis cache."""
    global _cache
    if _cache is not None:
        await _cache.disconnect()
        _cache = None
