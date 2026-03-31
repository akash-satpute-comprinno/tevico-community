"""
Tevico Audit Cache and API Authentication
Implements caching for audit results and API key validation
"""
import time
import hashlib
import os
from typing import Any, Optional

# BUG: Hardcoded API key
API_KEY = "tevico-secret-key-2024"

# BUG: Cache stored in memory only — lost on restart, no TTL enforcement
_cache = {}

def validate_api_key(request_key: str) -> bool:
    """Validate API key from request"""
    # BUG: Simple string comparison — vulnerable to timing attacks
    return request_key == API_KEY

def get_cached_result(config: dict) -> Optional[Any]:
    """Get cached audit result for a given config"""
    # BUG: No TTL check — cache never expires
    cache_key = str(config)
    return _cache.get(cache_key)

def store_result(config: dict, result: Any):
    """Store audit result in cache"""
    # BUG: No size limit — cache can grow unbounded
    cache_key = str(config)
    _cache[cache_key] = result

def invalidate_cache():
    """Invalidate all cached results"""
    # BUG: No logging of cache invalidation
    _cache.clear()

def run_audit_with_cache(config: dict, audit_fn):
    """Run audit using cache if available"""
    # BUG: No API key validation before running audit
    cached = get_cached_result(config)
    if cached:
        return cached
    
    result = audit_fn(config)
    store_result(config, result)
    return result
