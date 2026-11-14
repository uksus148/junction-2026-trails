import asyncio
import json
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest

from gopstop_agent.config import Settings
from gopstop_agent.discovery import DiscoveryResult, PlaceDiscovery, create_discovery
from gopstop_agent.intent import IntentClarificationRequired, ProviderError, RouteIntent


def settings(**overrides):
    return Settings(_env_file=None, anthropic_api_key="fixture-claude", exa_api_key="fixture-exa",
                    nominatim_user_agent="TrailsTest/1.0 team@example.org", **overrides)


def tool(name, value):
    return httpx.Response(200, json={"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "name": name, "input": value,
    }]})


def row(index, name, lat, lon):
    return {"osm_type": "node", "osm_id": index, "display_name": name, "lat": lat, "lon": lon}


def provider_fixture(intent, places, calls, region="High Tatras, Slovakia"):
    def handle(request):
        calls.append(request)
        body = json.loads(request.content) if request.content else {}
        if request.url.host == "api.anthropic.com":
            if body["tool_choice"]["name"] == "extract_route_intent":
                return tool("extract_route_intent", intent)
            evidence = json.loads(body["messages"][0]["content"])
            name = evidence["sources"][0]["title"]
            return tool("resolve_place", {"place": {
                "name": name, "geocodeQuery": f"{name}, {region}", "sourceIndex": 0, "tags": [],
            }})
        if request.url.host == "api.exa.ai":
            description = body["query"].removeprefix("Find hiking place: ").split(". Route context:")[0]
            index = list(places).index(description)
            name, _ = places[description]
            return httpx.Response(200, json={"results": [
                {"url": "ftp://invalid.example/"},
                {"title": name, "url": f"https://evidence.example/{index}", "text": f"Located in {region}"},
            ]})
        assert request.url.host == "nominatim.openstreetmap.org"
        assert request.headers["User-Agent"] == "TrailsTest/1.0 team@example.org"
        name = request.url.params["q"].removesuffix(f", {region}")
        rows = next(rows for title, rows in places.values() if title == name)
        return httpx.Response(200, json=rows)
    return handle


@pytest.fixture
async def cache():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


async def test_tatras_discovery_preserves_sources_coordinates_waypoint_order_and_history(cache):
    description = "the waterfall from TikTok near Štrbské Pleso"
    intent = {"start": "Štrbské Pleso", "end": "Rysy", "mustSee": [description],
              "preferences": ["wild scenery"]}
    places = {
        "Štrbské Pleso": ("Štrbské Pleso", [row(1, "Štrbské Pleso", 49.1191, 20.0627)]),
        description: ("Skok waterfall", [row(2, "Skok waterfall", 49.1425, 20.0506)]),
        "Rysy": ("Rysy", [row(3, "Rysy", 49.1795, 20.088)]),
    }
    calls = []
    history = [{"role": "user", "content": "Hike from Štrbské Pleso to Rysy"},
               {"role": "assistant", "content": "Any places to see?"}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider_fixture(intent, places, calls))) as client:
        discovery = create_discovery(client, cache, settings())
        for _ in range(2):
            result = await discovery.discover("Via the waterfall, I love wild scenery", history)
            assert result.ready_for_handoff
            assert result.stops[0].place.name == "Skok waterfall"
            assert (result.stops[0].place.location.lat, result.stops[0].place.location.lon) == (49.1425, 20.0506)
            assert str(result.stops[0].place.source.sourceUrl) == "https://evidence.example/1"
            assert result.stops[0].place.location.osm_id == 2
            assert result.intent.preferences == ["wild scenery"]
            assert result.unresolved == [] and "OpenStreetMap" in result.attribution
            payload = result.model_dump()
            assert "id" not in payload["stops"][0]["place"] and "routeId" not in payload
    assert sum(r.url.host == "api.exa.ai" for r in calls) == 3
    assert sum(r.url.host == "nominatim.openstreetmap.org" for r in calls) == 3
    resolution = [r for r in calls if r.url.host == "api.anthropic.com"
                  and json.loads(r.content)["tool_choice"]["name"] == "resolve_place"]
    assert len(resolution) == 3  # Three cold resolutions, none on the repeated discovery.
    extraction = [json.loads(r.content) for r in calls if r.url.host == "api.anthropic.com"
                  and json.loads(r.content)["tool_choice"]["name"] == "extract_route_intent"]
    assert all(body["messages"][:-1] == history for body in extraction)


async def test_other_regions_ambiguity_and_missing_endpoints_keep_evidence_for_clarification(cache):
    intent = {"start": "Tromsø", "mustSee": ["a nearby castle"], "end": None}
    places = {
        "Tromsø": ("Tromsø", [row(1, "Tromsø", 69.65, 18.96)]),
        "a nearby castle": ("Castle", [row(2, "Castle", 69.66, 18.97), row(3, "Castle", 69.67, 18.98)]),
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider_fixture(intent, places, [], "Norway"))) as client:
        result = await create_discovery(client, cache, settings()).discover("Hike near Tromsø", [])
    assert not result.ready_for_handoff
    assert result.unresolved == ["a nearby castle"] and result.missing_endpoints == ["end"]
    assert result.stops[0].place is None and result.stops[0].sources


async def test_duplicate_targets_reuse_research_without_losing_requested_visit_order(cache):
    intent = {"start": "Skok", "end": "Skok", "mustSee": ["Skok", "Skok"]}
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider_fixture(
        intent, {"Skok": ("Skok", [row(2, "Skok", 49.1425, 20.0506)])}, calls,
    ))) as client:
        result = await create_discovery(client, cache, settings()).discover("Return to Skok", [])
    assert result.ready_for_handoff and len(result.stops) == 2
    assert result.start.place == result.end.place == result.stops[0].place
    assert len(calls) == 4  # Intent, Exa, source resolution, geocoding.


async def test_excess_stops_propagate_clarification_before_research(cache):
    calls = []

    def handle(request):
        calls.append(request)
        assert request.url.host == "api.anthropic.com"
        return tool("extract_route_intent", {"mustSee": [f"stop {i}" for i in range(6)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(IntentClarificationRequired):
            await create_discovery(client, cache, settings()).discover("Six stops, please", [])
    assert len(calls) == 1


async def test_whole_discovery_deadline_cancels_work_before_any_research():
    stopped = asyncio.Event()

    async def stall(*_):
        try:
            await asyncio.sleep(10)
        finally:
            stopped.set()

    intent, search = AsyncMock(), AsyncMock()
    intent.extract.side_effect = stall
    discovery = PlaceDiscovery(intent, search, AsyncMock(), AsyncMock(), timeout_seconds=0.01)
    with pytest.raises(ProviderError, match="time limit"):
        await discovery.discover("Find a waterfall", [])
    assert stopped.is_set()
    search.search.assert_not_awaited()


async def test_factory_requires_live_keys_and_empty_results_are_not_ready(cache):
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="requires ANTHROPIC_API_KEY and EXA_API_KEY"):
            create_discovery(client, cache, Settings(_env_file=None, anthropic_api_key="", exa_api_key=""))
    assert not DiscoveryResult(intent=RouteIntent(start="A", end="B")).ready_for_handoff
