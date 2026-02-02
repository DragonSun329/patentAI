"""Redis caching service."""
import json
import hashlib
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings


class CacheService:
    """Redis-based caching for search results and embeddings."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.ttl = settings.cache_ttl
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key."""
        return f"patentai:{prefix}:{identifier}"
    
    def _hash_query(self, query: str) -> str:
        """Hash a query string for cache key."""
        return hashlib.md5(query.encode()).hexdigest()
    
    async def get_embedding(self, text_hash: str) -> Optional[list]:
        """Get cached embedding."""
        if not self.redis:
            return None
        
        key = self._make_key("embed", text_hash)
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def set_embedding(self, text_hash: str, embedding: list):
        """Cache an embedding."""
        if not self.redis:
            return
        
        key = self._make_key("embed", text_hash)
        await self.redis.setex(
            key,
            self.ttl * 24,  # Embeddings cached longer (24x)
            json.dumps(embedding)
        )
    
    async def get_search_results(self, query: str) -> Optional[list]:
        """Get cached search results."""
        if not self.redis:
            return None
        
        key = self._make_key("search", self._hash_query(query))
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def set_search_results(self, query: str, results: list):
        """Cache search results."""
        if not self.redis:
            return
        
        key = self._make_key("search", self._hash_query(query))
        await self.redis.setex(
            key,
            self.ttl,
            json.dumps(results)
        )
    
    async def get_analysis(self, source_id: str, target_id: str) -> Optional[dict]:
        """Get cached infringement analysis."""
        if not self.redis:
            return None
        
        key = self._make_key("analysis", f"{source_id}:{target_id}")
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def set_analysis(self, source_id: str, target_id: str, analysis: dict):
        """Cache infringement analysis."""
        if not self.redis:
            return
        
        key = self._make_key("analysis", f"{source_id}:{target_id}")
        await self.redis.setex(
            key,
            self.ttl * 24,  # Analysis cached longer
            json.dumps(analysis)
        )
    
    async def increment_counter(self, name: str) -> int:
        """Increment a counter (for metrics)."""
        if not self.redis:
            return 0
        
        key = self._make_key("counter", name)
        return await self.redis.incr(key)
    
    async def get_counter(self, name: str) -> int:
        """Get counter value."""
        if not self.redis:
            return 0
        
        key = self._make_key("counter", name)
        val = await self.redis.get(key)
        return int(val) if val else 0


# Singleton instance
cache_service = CacheService()
