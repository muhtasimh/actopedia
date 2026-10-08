import asyncio
from unittest.mock import AsyncMock, patch

import redis.asyncio as redis

from app.cache import cache_key, get_json


def test_cache_key_ignores_param_order():
    assert cache_key("/movie/1", {"a": 1, "b": 2}) == cache_key(
        "/movie/1", {"b": 2, "a": 1}
    )


def test_cache_hit_skips_upstream():
    client = AsyncMock()
    client.get.return_value = '{"results":[1]}'
    fetch = AsyncMock(return_value={"results": [2]})
    with patch("app.cache.get_client", return_value=client):
        result = asyncio.run(get_json("/search/person", {"query": "x"}, fetch))
    assert result == {"results": [1]}
    fetch.assert_not_awaited()
    client.set.assert_not_awaited()


def test_cache_miss_writes_with_ttl():
    client = AsyncMock()
    client.get.return_value = None
    fetch = AsyncMock(return_value={"results": [2]})
    with patch("app.cache.get_client", return_value=client):
        result = asyncio.run(get_json("/search/person", {"query": "x"}, fetch, ttl=120))
    assert result == {"results": [2]}
    fetch.assert_awaited_once()
    assert client.set.await_args.kwargs["ex"] == 120


def test_redis_outage_falls_back_to_upstream():
    client = AsyncMock()
    client.get.side_effect = redis.RedisError("unavailable")
    fetch = AsyncMock(return_value={"results": [3]})
    with patch("app.cache.get_client", return_value=client):
        result = asyncio.run(get_json("/search/person", {}, fetch))
    assert result == {"results": [3]}
    fetch.assert_awaited_once()


def test_upstream_failure_is_not_cached():
    client = AsyncMock()
    client.get.return_value = None
    fetch = AsyncMock(side_effect=RuntimeError("TMDB unavailable"))
    with patch("app.cache.get_client", return_value=client):
        try:
            asyncio.run(get_json("/movie/1", {}, fetch))
            assert False, "expected upstream failure"
        except RuntimeError:
            pass
    client.set.assert_not_awaited()
