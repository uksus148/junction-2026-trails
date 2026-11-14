import json
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest
from redis.exceptions import ConnectionError

from gopstop_agent.exa import ExaSearch
from gopstop_agent.intent import ProviderError


@pytest.fixture
async def cache():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


async def test_search_retains_sources_and_reuses_cache_for_one_day(cache):
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["x-api-key"] == "fixture-key"
        assert request.extensions["timeout"]["read"] == 0.5
        assert json.loads(request.content)["query"] == "Skok waterfall High Tatras"
        return httpx.Response(200, json={"results": [{
            "title": "Skok waterfall", "url": "https://example.org/skok", "text": "Trail description",
        }]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        search = ExaSearch(client, cache, "fixture-key", timeout_seconds=0.5)
        first = await search.search("Skok waterfall High Tatras")
        assert await search.search("  Skok waterfall High Tatras  ") == first
    assert len(calls) == 1
    assert first[0].model_dump(mode="json") == {
        "title": "Skok waterfall", "sourceUrl": "https://example.org/skok", "text": "Trail description",
    }
    keys = await cache.keys("gopstop:exa-text:v1:*")
    assert len(keys) == 1 and "Skok" not in keys[0]
    assert 0 < await cache.ttl(keys[0]) <= 86400


async def test_queries_have_separate_caches_and_empty_results_are_cached(cache):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        search = ExaSearch(client, cache, "fixture")
        for query in ["Tatras waterfall", "Tromsø viewpoint", "Tatras waterfall"]:
            assert await search.search(query) == []
    assert len(calls) == 2


async def test_corrupt_cache_refreshes_and_missing_metadata_keeps_source(cache):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, json={"results": [{"url": "https://example.org/trail", "title": None, "text": None}]},
    ))) as client:
        search = ExaSearch(client, cache, "fixture")
        await search.search("trail")
        key, = await cache.keys("gopstop:exa-text:v1:*")
        await cache.set(key, "invalid cache JSON")
        result = await search.search("trail")
        assert str(result[0].sourceUrl) == "https://example.org/trail"
        assert result[0].text == ""
        assert json.loads(await cache.get(key))[0]["sourceUrl"] == "https://example.org/trail"


@pytest.mark.parametrize("body", [{}, {"results": None}, {"results": [{"url": "javascript:bad"}]}])
async def test_malformed_provider_results_are_rejected(cache, body):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=body),
    )) as client:
        with pytest.raises(ProviderError):
            await ExaSearch(client, cache, "fixture").search("trail")
    assert await cache.keys("gopstop:exa-text:v1:*") == []


@pytest.mark.parametrize("failure", [429, httpx.ReadTimeout])
async def test_provider_failures_are_not_retried_or_cached(cache, failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == 429:
            return httpx.Response(429, text="private upstream details")
        raise failure("private upstream details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError) as error:
            await ExaSearch(client, cache, "fixture").search("trail")
    assert len(calls) == 1 and "private" not in str(error.value)
    assert await cache.keys("gopstop:exa-text:v1:*") == []


async def test_cache_failure_does_not_spend_provider_credits():
    redis = AsyncMock()
    redis.get.side_effect = ConnectionError("fixture cache outage")
    web = AsyncMock()
    with pytest.raises(ConnectionError):
        await ExaSearch(web, redis, "fixture").search("trail")
    web.post.assert_not_awaited()


async def test_blank_query_does_not_call_cache_or_provider():
    redis, web = AsyncMock(), AsyncMock()
    with pytest.raises(ValueError, match="blank"):
        await ExaSearch(web, redis, "fixture").search("  ")
    redis.get.assert_not_awaited()
    web.post.assert_not_awaited()


@pytest.mark.parametrize("bad", [
    {"url": "ftp://example.org/bad"}, {"title": "missing URL"},
    {"url": "https://example.org/bad", "title": "x" * 2001},
])
async def test_mixed_results_keep_valid_sources_and_cache_them(cache, bad):
    rows = [{"url": "https://example.org/first"}, bad, {"url": "https://example.org/second"}]
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"results": rows})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        search = ExaSearch(client, cache, "fixture")
        for _ in range(2):
            sources = await search.search("waterfalls")
            assert [str(s.sourceUrl) for s in sources] == [
                "https://example.org/first", "https://example.org/second",
            ]
    assert len(calls) == 1


async def test_cache_write_failure_propagates_after_one_paid_call():
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.side_effect = ConnectionError("fixture write outage")
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ConnectionError):
            await ExaSearch(client, redis, "fixture").search("trail")
    assert len(calls) == 1
