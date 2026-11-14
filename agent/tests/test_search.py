import json
import asyncio
import time

import fakeredis.aioredis
import httpx
import pytest

from gopstop_agent.intent import ProviderError
from gopstop_agent.search import ExaSearch, NominatimGeocoder, cache_key


async def test_exa_retains_sources_and_caches_for_one_day():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    calls = []
    result = {"title": "Skok waterfall", "url": "https://example.org/skok", "text": "High Tatras"}

    def handle(request):
        calls.append(request)
        assert json.loads(request.content)["query"] == "Skok waterfall"
        return httpx.Response(200, json={"results": [result]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        search = ExaSearch(client, redis, "fixture-key")
        for _ in range(2):
            sources = await search.search("Skok waterfall")
            assert sources[0].model_dump(mode="json") == result
    assert len(calls) == 1
    assert 0 < await redis.ttl(cache_key("exa", "Skok waterfall")) <= 86400
    await redis.aclose()


@pytest.mark.parametrize("body", [{}, {"results": [{"url": "javascript:bad"}]}, {"results": None}])
async def test_exa_rejects_invalid_results(body):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=body),
    )) as client:
        with pytest.raises(ProviderError):
            await ExaSearch(client, redis, "fixture").search("waterfall")
    await redis.aclose()


async def test_geocoding_preserves_coordinate_order_and_caches():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["User-Agent"] == "Trails/1.0 team@example.org"
        assert request.url.params["q"] == "Skok, High Tatras, Slovakia"
        return httpx.Response(200, json=[{
            "osm_type": "node", "osm_id": 123, "display_name": "Skok waterfall",
            "lat": "49.166", "lon": "20.061",
        }])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        geocoder = NominatimGeocoder(client, redis, "Trails/1.0 team@example.org")
        for _ in range(2):
            place = await geocoder.geocode("Skok, High Tatras, Slovakia")
            assert (place.lat, place.lon, place.id) == (49.166, 20.061, "osm:node:123")
    assert len(calls) == 1
    await redis.aclose()


@pytest.mark.parametrize("candidates", [[], [{}, {}]])
async def test_missing_or_ambiguous_geocoding_is_not_guessed(candidates):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=candidates),
    )) as client:
        geocoder = NominatimGeocoder(client, redis, "Trails/1.0")
        assert await geocoder.geocode("unspecified waterfall") is None
        assert await geocoder.geocode("unspecified waterfall") is None
    await redis.aclose()


async def test_geocoding_rejects_out_of_range_coordinates():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[{
        "osm_type": "node", "osm_id": 1, "display_name": "bad", "lat": 200, "lon": 49,
    }]))) as client:
        with pytest.raises(ProviderError):
            await NominatimGeocoder(client, redis, "Trails/1.0").geocode("bad")
    await redis.aclose()


async def test_geocoding_gate_is_shared_between_provider_instances():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    requested_at = []

    def handle(_):
        requested_at.append(time.monotonic())
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        first = NominatimGeocoder(client, redis, "Trails/1.0")
        second = NominatimGeocoder(client, redis, "Trails/1.0")
        await asyncio.gather(first.geocode("first"), second.geocode("second"))
    assert len(requested_at) == 2
    assert requested_at[1] - requested_at[0] >= 0.95
    await redis.aclose()
