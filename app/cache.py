"""Optional Redis cache for TMDB JSON responses.

Set REDIS_URL in the deployment environment to enable caching.
Without Redis (or during a Redis outage), requests go directly to TMDB.
"""
import hashlib
import json
import logging
import os

import redis.asyncio as redis

logger = logging.getLogger(__name__)
_client = None
_client_url = None


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


async def get_json(path, params, fetch, ttl=3600):
    """Cache successful responses only; never cache upstream failures."""
    client = get_client()
    key = cache_key(path, params)
    if client is not None:
        try:
            cached = await client.get(key)
            if cached is not None:
                return json.loads(cached)
        except (redis.RedisError, OSError, ValueError) as exc:
            logger.warning("Redis read failed; using TMDB: %s", exc)

    data = await fetch()
    if client is not None:
        try:
            await client.set(key, json.dumps(data), ex=ttl)
        except (redis.RedisError, OSError) as exc:
            logger.warning("Redis write failed; returning TMDB response: %s", exc)
    return data
