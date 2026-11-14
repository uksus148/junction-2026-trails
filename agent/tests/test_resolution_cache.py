import asyncio
import json
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest
from redis.exceptions import ConnectionError

from gopstop_agent.exa import ResearchSource
from gopstop_agent.intent import ProviderError, ProviderTimeout
from gopstop_agent.resolution_cache import CachedPlaceResolver
from gopstop_agent.resolver import ClaudePlaceResolver
from test_resolver import tool


PLACE = {"name": "Skok", "geocodeQuery": "Skok, High Tatras, Slovakia",
         "sourceIndex": 0, "tags": ["waterfall"]}
SOURCES = [ResearchSource(title="Skok", sourceUrl="https://evidence.example/skok", text="A Tatras waterfall.")]
PREFIX = "gopstop:place-resolution:v1:"


@pytest.fixture
async def cache():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def provider():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=tool(PLACE))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        yield client, calls


@pytest.mark.parametrize("resolved", [True, False])
async def test_results_and_ambiguity_survive_new_resolver_without_refreshing_ttl(cache, resolved):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=tool(PLACE if resolved else None))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        first = await CachedPlaceResolver(ClaudePlaceResolver(client, "private-key-one", "model"), cache).resolve(
            "Tatras waterfall", SOURCES,
        )
        key, = await cache.keys(PREFIX + "*")
        assert len(key.removeprefix(PREFIX)) == 64
        assert "Skok" not in key and "evidence" not in key and "private" not in key
        assert 0 < await cache.ttl(key) <= 86400
        await cache.expire(key, 100)
        if first is not None:
            first.name = "Caller mutation"
        second = await CachedPlaceResolver(ClaudePlaceResolver(client, "private-key-two", "model"), cache).resolve(
            "Tatras waterfall", SOURCES,
        )
    assert len(calls) == 1
    assert (second.model_dump() if resolved else second) == (PLACE if resolved else None)
    assert 0 < await cache.ttl(key) <= 100  # A hit must not reset the 24-hour lifetime.
    assert json.loads(await cache.get(key)) == (PLACE if resolved else None)


@pytest.mark.parametrize("change", ["description", "model", "title", "url", "text", "order", "prompt", "schema"])
async def test_effective_request_changes_cannot_reuse_a_different_resolution(cache, provider, monkeypatch, change):
    client, calls = provider
    sources = [*SOURCES, ResearchSource(title="Rysy", sourceUrl="https://evidence.example/rysy", text="A peak.")]
    original = ClaudePlaceResolver(client, "fixture", "model")
    await CachedPlaceResolver(original, cache).resolve("Skok", sources)
    changed_sources = [source.model_copy(deep=True) for source in sources]
    resolver = ClaudePlaceResolver(client, "fixture", "other-model" if change == "model" else "model")
    description = "Rysy" if change == "description" else "Skok"
    if change in ("title", "url", "text"):
        field = "sourceUrl" if change == "url" else change
        value = "https://other.example/" if change == "url" else "Changed evidence"
        changed_sources[0] = ResearchSource.model_validate({**changed_sources[0].model_dump(), field: value})
    if change == "order":
        changed_sources.reverse()
    if change in ("prompt", "schema"):
        build = resolver.request_body

        def changed_body(*args):
            body = build(*args)
            if change == "prompt":
                body["system"] += " New grounding instruction."
            else:
                body["tools"][0]["input_schema"]["description"] = "Revised schema."
            return body

        monkeypatch.setattr(resolver, "request_body", changed_body)
    await CachedPlaceResolver(resolver, cache).resolve(description, changed_sources)
    assert len(calls) == 2 and len(await cache.keys(PREFIX + "*")) == 2
    assert json.loads(calls[0].content) != json.loads(calls[1].content)


async def test_only_the_three_sources_actually_sent_to_claude_affect_cache(cache, provider):
    client, calls = provider
    resolver = CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache)
    first_three = SOURCES * 3
    await resolver.resolve("Skok", first_three)
    await resolver.resolve("Skok", [*first_three, ResearchSource(title="Ignored", sourceUrl="https://ignored.example/")])
    assert len(calls) == 1
    assert len(json.loads(json.loads(calls[0].content)["messages"][0]["content"])["sources"]) == 3


@pytest.mark.parametrize("corrupt", [
    "invalid JSON", "{}", '"null"', "[]",
    json.dumps({**PLACE, "sourceIndex": 1}),
    json.dumps({**PLACE, "sourceIndex": True}),
    json.dumps({**PLACE, "name": " "}),
    json.dumps({**PLACE, "sourceUrl": "https://invented.example/"}),
])
async def test_corrupt_or_out_of_range_cached_results_refresh_once(cache, provider, corrupt):
    client, calls = provider
    resolver = CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache)
    await resolver.resolve("Skok", SOURCES)
    key, = await cache.keys(PREFIX + "*")
    await cache.set(key, corrupt)
    assert (await resolver.resolve("Skok", SOURCES)).model_dump() == PLACE
    assert len(calls) == 2 and json.loads(await cache.get(key)) == PLACE
    assert 0 < await cache.ttl(key) <= 86400


async def test_expired_resolution_requires_new_provider_work(cache, provider):
    client, calls = provider
    resolver = CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache)
    await resolver.resolve("Skok", SOURCES)
    key, = await cache.keys(PREFIX + "*")
    await cache.pexpire(key, 1)
    await asyncio.sleep(0.01)
    assert not await cache.exists(key)
    await resolver.resolve("Skok", SOURCES)
    assert len(calls) == 2


@pytest.mark.parametrize("failure", ["http", "timeout", "truncated", "invalid_source"])
async def test_provider_failures_are_not_cached_or_automatically_retried(cache, failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == "http":
            return httpx.Response(429, text="private provider details")
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider details")
        if failure == "truncated":
            return httpx.Response(200, json={"stop_reason": "max_tokens", "content": []})
        return httpx.Response(200, json=tool({**PLACE, "sourceIndex": 1}))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        resolver = CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache)
        with pytest.raises(ProviderError) as error:
            await resolver.resolve("Skok", SOURCES)
    assert "private" not in str(error.value)
    assert isinstance(error.value, ProviderTimeout) == (failure == "timeout")
    assert len(calls) == 1 and await cache.keys(PREFIX + "*") == []


@pytest.mark.parametrize("operation", ["get", "set"])
async def test_cache_outages_stop_without_bypass_or_paid_retries(provider, operation):
    client, calls = provider
    cache = AsyncMock()
    cache.get.return_value = None
    getattr(cache, operation).side_effect = ConnectionError("private cache details")
    with pytest.raises(ConnectionError):
        await CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache).resolve("Skok", SOURCES)
    assert len(calls) == (0 if operation == "get" else 1)
    if operation == "get":
        cache.set.assert_not_awaited()


async def test_no_evidence_uses_neither_cache_nor_provider():
    cache, resolver = AsyncMock(), AsyncMock()
    assert await CachedPlaceResolver(resolver, cache).resolve("Unknown waterfall", []) is None
    cache.get.assert_not_awaited()
    cache.set.assert_not_awaited()
    resolver.resolve.assert_not_awaited()


async def test_cancellation_does_not_cache_an_unfinished_resolution(cache):
    stopped = asyncio.Event()

    async def handle(request):
        try:
            await asyncio.sleep(10)
        finally:
            stopped.set()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        resolver = CachedPlaceResolver(ClaudePlaceResolver(client, "fixture", "model"), cache)
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.01):
                await resolver.resolve("Skok", SOURCES)
    assert stopped.is_set() and await cache.keys(PREFIX + "*") == []
