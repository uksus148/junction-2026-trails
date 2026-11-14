import asyncio
import time

import fakeredis.aioredis
import httpx
import pytest

from gopstop_agent.geocoding import NominatimGeocoder
from gopstop_agent.intent import ProviderError


ROW = {"osm_type": "node", "osm_id": 123, "display_name": "Skok waterfall",
       "lat": "49.1425", "lon": "20.0506"}


@pytest.fixture
async def cache():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


async def test_coordinates_attribution_request_identity_and_cache(cache):
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["User-Agent"] == "Trails/1.0 team@example.org"
        assert request.url.params["q"] == "Skok, High Tatras, Slovakia"
        assert request.url.params["limit"] == "2"
        assert request.extensions["timeout"]["read"] == 2
        return httpx.Response(200, json=[ROW])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        geocoder = NominatimGeocoder(client, cache, "Trails/1.0 team@example.org", timeout_seconds=2)
        first = await geocoder.geocode("Skok, High Tatras, Slovakia")
        assert await geocoder.geocode("Skok, High Tatras, Slovakia") == first
    assert len(calls) == 1
    assert (first.lat, first.lon) == (49.1425, 20.0506)
    assert first.osm_url == "https://www.openstreetmap.org/node/123"
    key, = await cache.keys("gopstop:nominatim:result:v1:*")
    assert 0 < await cache.ttl(key) <= 86400


@pytest.mark.parametrize("rows", [[], [ROW, {**ROW, "osm_id": 456}]])
async def test_missing_and_ambiguous_locations_remain_unresolved_and_cached(cache, rows):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=rows)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        geocoder = NominatimGeocoder(client, cache, "Trails/1.0")
        assert await geocoder.geocode("waterfall") is None
        assert await geocoder.geocode("waterfall") is None
    assert len(calls) == 1


@pytest.mark.parametrize("rows", [[{**ROW, "lat": "NaN"}], [{**ROW, "lon": 181}],
                                  [{**ROW, "osm_type": "unknown"}], {"error": "bad"}])
async def test_invalid_geocoding_output_is_not_cached(cache, rows):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=rows),
    )) as client:
        with pytest.raises(ProviderError):
            await NominatimGeocoder(client, cache, "Trails/1.0").geocode("invalid")
    assert await cache.keys("gopstop:nominatim:result:v1:*") == []


async def test_shared_gate_waits_until_one_second_after_previous_response(cache):
    started, finished = [], []

    async def handle(request):
        started.append(time.monotonic())
        await asyncio.sleep(0.05)
        finished.append(time.monotonic())
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        first = NominatimGeocoder(client, cache, "Trails/1.0")
        second = NominatimGeocoder(client, cache, "Trails/1.0")
        await asyncio.gather(first.geocode("first"), second.geocode("second"))
    assert len(started) == 2
    assert started[1] - finished[0] >= 0.95


async def test_gate_wait_has_a_deadline_and_does_not_release_another_worker(cache):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: pytest.fail("A busy gate must prevent the HTTP request"),
    )) as client:
        geocoder = NominatimGeocoder(client, cache, "Trails/1.0", timeout_seconds=0.05)
        await cache.set(geocoder._gate, "other-worker", ex=10)
        with pytest.raises(ProviderError):
            await geocoder.geocode("busy")
        assert await cache.get(geocoder._gate) == "other-worker"


async def test_http_failure_is_not_retried_and_cools_down_the_gate(cache):
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("private details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        geocoder = NominatimGeocoder(client, cache, "Trails/1.0")
        with pytest.raises(ProviderError) as error:
            await geocoder.geocode("timeout")
        assert 0 < await cache.pttl(geocoder._gate) <= 1000
    assert len(calls) == 1 and "private" not in str(error.value)


async def test_expired_workers_do_not_change_a_new_gate_owner(cache):
    async def handle(request):
        await cache.set(geocoder._gate, "new-worker", ex=10)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        geocoder = NominatimGeocoder(client, cache, "Trails/1.0")
        await geocoder.geocode("fixture")
        assert await cache.get(geocoder._gate) == "new-worker"
        assert await cache.pttl(geocoder._gate) > 5000
