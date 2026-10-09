"""Optional Redis cache for TMDB JSON responses.

Set REDIS_URL in the deployment environment to enable caching.
Without Redis (or during a Redis outage), requests go directly to TMDB.
"""
import hashlib
import json
import logging
import os
import time
from collections import OrderedDict

import redis.asyncio as redis

logger = logging.getLogger(__name__)
_client = None
_client_url = None
_memory = OrderedDict()
_MAX_MEMORY_ENTRIES = 2000


def get_client():
    global _client, _client_url
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    if _client is None or _client_url != url:
        _client = redis.from_url(
            url, decode_responses=True, socket_connect_timeout=1,
            socket_timeout=1, retry_on_timeout=False,
        )
        _client_url = url
    return _client


def cache_key(path, params):
    payload = json.dumps([path, params or {}], sort_keys=True)
    return "tmdb:v1:" + hashlib.sha256(payload.encode()).hexdigest()


def _remember(key, data, ttl):
    if ttl <= 0:
        return
    _memory[key] = (time.monotonic() + ttl, data)
    _memory.move_to_end(key)
    while len(_memory) > _MAX_MEMORY_ENTRIES:
        _memory.popitem(last=False)


async def get_json(path, params, fetch, ttl=3600):
    """Cache successful responses in memory and optionally Redis."""
    key = cache_key(path, params)
    entry = _memory.get(key)
    if entry is not None:
        expires_at, data = entry
        if time.monotonic() < expires_at:
            _memory.move_to_end(key)
            return data
        del _memory[key]

    client = get_client()
    if client is not None:
        try:
            cached = await client.get(key)
            if cached is not None:
                data = json.loads(cached)
                _remember(key, data, ttl)
                return data
        except (redis.RedisError, OSError, ValueError) as exc:
            logger.warning("Redis read failed; using TMDB: %s", exc)

    data = await fetch()
    _remember(key, data, ttl)
    if client is not None:
        try:
            await client.set(key, json.dumps(data), ex=ttl)
        except (redis.RedisError, OSError) as exc:
            logger.warning("Redis write failed; returning TMDB response: %s", exc)
    return data
