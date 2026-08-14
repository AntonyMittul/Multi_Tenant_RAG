import redis
import hashlib
import json
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Redis client for caching
# (We reuse the Celery broker URL for simplicity in this project)
try:
    cache_client = redis.from_url(settings.CELERY_BROKER_URL)
except Exception as e:
    logger.error(f"Failed to connect to Redis cache: {str(e)}")
    cache_client = None

def get_cache_key(tenant_id: str, query: str) -> str:
    """Generate a consistent cache key for a tenant and query."""
    # We use a hash to ensure the key is a reasonable length and safe
    query_hash = hashlib.md5(query.lower().strip().encode('utf-8')).hexdigest()
    return f"cache:{tenant_id}:{query_hash}"

def get_cached_response(tenant_id: str, query: str) -> Optional[dict]:
    """Retrieve a cached response if it exists."""
    if not cache_client:
        return None
        
    try:
        key = get_cache_key(tenant_id, query)
        cached_data = cache_client.get(key)
        if cached_data:
            logger.info(f"Cache hit for query: '{query}' (Tenant: {tenant_id})")
            return json.loads(cached_data)
        return None
    except Exception as e:
        logger.warning(f"Error reading from cache: {str(e)}")
        return None

def set_cached_response(tenant_id: str, query: str, response_data: dict, ttl_seconds: int = 3600):
    """Store a response in the cache with a time-to-live (default 1 hour)."""
    if not cache_client:
        return
        
    try:
        key = get_cache_key(tenant_id, query)
        cache_client.setex(key, ttl_seconds, json.dumps(response_data))
    except Exception as e:
        logger.warning(f"Error writing to cache: {str(e)}")

