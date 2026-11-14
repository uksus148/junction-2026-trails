import asyncio
import json

import httpx
import pytest

from gopstop_agent.config import Settings
from gopstop_agent.discovery import DiscoveryResult, PlaceFinding
from gopstop_agent.handoff import RouteHandoff, create_handoff
from gopstop_agent.intent import RouteIntent
from gopstop_agent.trails_api import HandoffError, NoHikingRoute, TrailsApi
from test_trails_api import candidate, identifier, place, problem, route


def discovery(stops=(2,), start=1, end=3):
    def finding(index):
        value = candidate(index)
        return PlaceFinding(description=value.name, sources=[value.source], place=value)
    return DiscoveryResult(
        intent=RouteIntent(start=f"Place {start}", end=f"Place {end}",
                           mustSee=[f"Place {i}" for i in stops], preferences=["wild scenery"]),
        start=finding(start), stops=[finding(i) for i in stops], end=finding(end),
    )


class ApiFixture:
    def __init__(self, failure=None):
        self.calls = []
        self.rows = {}
        self.saved_route = None
        self.failure = failure

    def __call__(self, request):
        self.calls.append(request)
        if request.url.path == "/api/places":
            body = json.loads(request.content)
            index = body["provenance"]["osmId"]
            # A replay can have earlier canonical names, coordinates, tags and source.
            key = (body["provenance"]["osmType"], index)
            if key in self.rows:
                return httpx.Response(200, json=self.rows[key])
            public_index = index if key[0] == "node" else index + 1000
            self.rows[key] = place(public_index, source=body["provenance"]["sourceUrl"])
            return httpx.Response(201, json=self.rows[key])
        if request.method == "POST":
            assert request.url.path == "/api/routes"
            if self.failure == "no_route":
                return httpx.Response(422, json=problem())
            if self.failure == "storage":
                return httpx.Response(503, json=problem("storage_unavailable", 503))
            body = json.loads(request.content)
            by_id = {row["id"]: row for row in self.rows.values()}
            self.saved_route = route([by_id[key] for key in body["placeIds"]])
            if self.failure == "stop_order":
                self.saved_route["places"].reverse()
            return httpx.Response(201, json=self.saved_route)
        assert request.method == "GET" and not request.content
        assert request.url.path == f"/api/routes/{identifier(99)}"
        if self.failure == "missing_route":
            return httpx.Response(404, json=problem("route_not_found", 404))
        if self.failure == "get_stop_order":
            self.saved_route["places"].reverse()
        return httpx.Response(200, json=self.saved_route)


async def test_handoff_uses_authoritative_coordinates_order_and_sources_then_fetches_route():
    fixture = ApiFixture()
    fixture.rows[("node", 1)] = place(1, name="Canonical start", lat=50.1, lon=21.1,
                                        source="https://older.example/start")
    result = discovery((2, 4, 2))
    async with httpx.AsyncClient(transport=httpx.MockTransport(fixture)) as client:
        saved = await create_handoff(client, Settings(_env_file=None, api_base_url="https://api.example")).persist(result)
    assert [str(p.id) for p in saved.places] == [identifier(i) for i in (1, 2, 4, 3)]
    assert [str(p.id) for p in saved.route.places] == [identifier(i) for i in (2, 4, 2)]
    assert saved.places[0].name == "Canonical start"
    assert saved.places[0].source == "https://older.example/start"
    assert result.start.place.source.sourceUrl.host == "source.example"  # Original evidence remains intact.
    assert "OpenStreetMap" in saved.attribution
    request = next(r for r in fixture.calls if r.method == "POST" and r.url.path == "/api/routes")
    assert json.loads(request.content) == {
        "start": {"lat": 50.1, "lon": 21.1}, "end": {"lat": 49.003, "lon": 20.003},
        "placeIds": [identifier(i) for i in (2, 4, 2)], "preferences": ["wild scenery"],
    }
    assert [r.method for r in fixture.calls] == ["POST"] * 5 + ["GET"]
    assert saved.route.model_dump(mode="json")["geojson"]["coordinates"][0] == [20.001, 49.001]


@pytest.mark.parametrize("stops,start,end", [((), 1, 3), ((1, 1), 1, 1)])
async def test_direct_hike_and_repeated_endpoints_preserve_visits_without_repeated_ingestion(stops, start, end):
    fixture = ApiFixture()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fixture)) as client:
        saved = await RouteHandoff(TrailsApi(client, "https://api.example")).persist(discovery(stops, start, end))
    assert [str(p.id) for p in saved.route.places] == [identifier(i) for i in stops]
    assert len([r for r in fixture.calls if r.url.path == "/api/places"]) == len({start, *stops, end})
    assert len(saved.places) == len({start, *stops, end})


async def test_osm_type_is_part_of_identity_not_just_numeric_id():
    fixture = ApiFixture()
    result = discovery((), 1, 1)
    result.end.place.location.osm_type = "way"
    async with httpx.AsyncClient(transport=httpx.MockTransport(fixture)) as client:
        saved = await RouteHandoff(TrailsApi(client, "https://api.example")).persist(result)
    assert set(fixture.rows) == {("node", 1), ("way", 1)}
    assert len(saved.places) == 2


@pytest.mark.parametrize("missing", ["start", "stop", "end", "intent"])
async def test_incomplete_discovery_never_writes(missing):
    result = discovery()
    if missing == "intent":
        result.intent.end = None
    elif missing == "stop":
        result.stops[0].place = None
    else:
        setattr(result, missing, None)
    fixture = ApiFixture()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fixture)) as client:
        with pytest.raises(ValueError, match="Resolve every"):
            await RouteHandoff(TrailsApi(client, "https://api.example")).persist(result)
    assert fixture.calls == []


@pytest.mark.parametrize("failure", ["no_route", "storage", "missing_route", "stop_order", "get_stop_order"])
async def test_route_failure_returns_no_result_and_keeps_prior_places_without_retry(failure):
    fixture = ApiFixture(failure)
    expected = NoHikingRoute if failure == "no_route" else HandoffError
    async with httpx.AsyncClient(transport=httpx.MockTransport(fixture)) as client:
        with pytest.raises(expected):
            await RouteHandoff(TrailsApi(client, "https://api.example")).persist(discovery((2, 4)))
    assert len(fixture.rows) == 4
    assert len([r for r in fixture.calls if r.method == "POST" and r.url.path == "/api/routes"]) == 1
    if failure == "storage":
        assert fixture.saved_route is None


async def test_total_deadline_cancels_request_and_never_retries_a_possible_committed_write():
    cancelled = asyncio.Event()
    calls = []

    async def handle(request):
        calls.append(request)
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(HandoffError) as error:
            await RouteHandoff(TrailsApi(client, "https://api.example"), 0.01).persist(discovery())
    assert error.value.status_code == 504 and cancelled.is_set() and len(calls) == 1


async def test_deadline_during_readback_leaves_saved_route_but_returns_no_success():
    fixture = ApiFixture()

    async def handle(request):
        response = fixture(request)
        if request.method == "GET":
            await asyncio.sleep(10)
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(HandoffError) as error:
            await RouteHandoff(TrailsApi(client, "https://api.example"), 0.02).persist(discovery())
    assert error.value.status_code == 504 and fixture.saved_route is not None
    assert len(fixture.calls) == 5  # Three ingestions, one route write, one readback.
