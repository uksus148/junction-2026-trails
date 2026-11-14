import copy
import json

import httpx
import pytest

from gopstop_agent.discovery import DiscoveredPlace
from gopstop_agent.trails_api import HandoffError, NoHikingRoute, TrailsApi, WaypointNotRoutable


def identifier(index):
    return f"00000000-0000-4000-8000-{index:012d}"


def candidate(index=1):
    return DiscoveredPlace.model_validate({
        "name": f"Place {index}", "tags": ["waterfall"],
        "source": {"title": "Research", "sourceUrl": f"https://source.example/{index}", "text": "Evidence"},
        "location": {"osm_type": "node", "osm_id": index, "display_name": f"Place {index}",
                     "lat": 49 + index / 1000, "lon": 20 + index / 1000},
    })


def place(index=1, **overrides):
    return {"id": identifier(index), "name": f"Place {index}", "lat": 49 + index / 1000,
            "lon": 20 + index / 1000, "tags": ["waterfall"], "photos": [],
            "source": f"https://source.example/{index}", **overrides}


def route(stops=()):
    return {"id": identifier(99), "geojson": {"type": "LineString",
            "coordinates": [[20.001, 49.001], [20.002, 49.002], [20.003, 49.003]]},
            "distanceKm": 7.5, "ascentM": 600, "durationMin": 150,
            "places": list(stops), "segments": []}


def problem(code="no_hiking_route", status=422):
    return {"type": "about:blank", "title": "Fixture error", "status": status,
            "detail": "Do not expose this remote detail.", "code": code}


@pytest.mark.parametrize("status", [200, 201])
async def test_ingestion_sends_complete_provenance_and_accepts_authoritative_records(status):
    calls = []
    saved = place(lat=50, source="https://older.example/evidence") if status == 200 else place()

    def handle(request):
        calls.append(request)
        assert request.url == "https://api.example/prefix/api/places"
        assert request.extensions["timeout"]["read"] == 3
        assert json.loads(request.content) == {
            "name": "Place 1", "lat": 49.001, "lon": 20.001, "tags": ["waterfall"],
            "provenance": {"sourceUrl": "https://source.example/1", "osmType": "node", "osmId": 1},
        }
        return httpx.Response(status, json=saved)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await TrailsApi(client, "https://api.example/prefix/", 3).ingest(candidate())
    assert result.model_dump(mode="json") == saved
    assert len(calls) == 1


@pytest.mark.parametrize("overrides", [
    {"source": "manual"}, {"source": "fixture"}, {"source": "javascript:alert(1)"},
    {"source": "https://invented.example/"}, {"id": "node/1"}, {"id": None},
    {"lat": 91}, {"lat": "49"}, {"lon": float("nan")}, {"photos": None},
])
async def test_invalid_or_manual_place_response_fails_closed(overrides):
    def handle(_):
        payload = place(**overrides)
        # Use a raw JSON body to exercise malformed non-finite wire values too.
        return httpx.Response(201, content=json.dumps(payload))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(HandoffError, match="invalid researched place"):
            await TrailsApi(client, "https://api.example").ingest(candidate())


@pytest.mark.parametrize("status,body,expected", [
    (422, problem(), NoHikingRoute),
    (422, problem("waypoint_not_routable"), WaypointNotRoutable),
    (422, {"code": "waypoint_not_routable"}, HandoffError),
    (422, problem("waypoint_not_routable", status=503), HandoffError),
    (422, problem("unknown_place"), HandoffError),
    (422, {"code": "no_hiking_route"}, HandoffError),
    (422, problem(status=503), HandoffError),
    (503, problem(), HandoffError),
    (502, problem(), HandoffError),
    (502, problem("waypoint_not_routable"), HandoffError),
])
async def test_only_verified_route_problem_is_a_normal_no_route_result(status, body, expected):
    from gopstop_agent.api_models import ApiPlace
    saved = ApiPlace.model_validate_json(json.dumps(place()))
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(expected) as error:
            await TrailsApi(client, "https://api.example").create_route(saved, saved, [], [])
    assert "remote detail" not in str(error.value)
    assert len(calls) == 1
    if isinstance(error.value, HandoffError):
        assert error.value.status_code == (503 if status == 503 else 502)


@pytest.mark.parametrize("failure,expected_status", [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)])
async def test_transport_failure_has_no_retry(failure, expected_status):
    calls = []

    def handle(request):
        calls.append(request)
        raise failure("secret remote URL/body", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(HandoffError) as error:
            await TrailsApi(client, "https://api.example").ingest(candidate())
    assert error.value.status_code == expected_status and "secret" not in str(error.value)
    assert len(calls) == 1


async def test_redirect_is_not_replayed_even_when_shared_client_follows_redirects():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(307, headers={"Location": "https://other.example/api/places"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), follow_redirects=True) as client:
        with pytest.raises(HandoffError):
            await TrailsApi(client, "https://api.example").ingest(candidate())
    assert len(calls) == 1


@pytest.mark.parametrize("corruption", ["id", "geometry", "coordinates", "distance", "stops", "photos"])
async def test_unusable_saved_route_is_rejected(corruption):
    payload = copy.deepcopy(route([place()]))
    if corruption == "id":
        payload["id"] = identifier(98)
    elif corruption == "geometry":
        payload["geojson"]["type"] = "Polygon"
    elif corruption == "coordinates":
        payload["geojson"]["coordinates"] = [[200, 49], [20, 49]]
    elif corruption == "distance":
        payload["distanceKm"] = -1
    elif corruption == "stops":
        payload.pop("places")
    else:
        payload["places"][0]["photos"] = [{"url": "https://photo.example/image.jpg"}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=payload),
    )) as client:
        with pytest.raises(HandoffError):
            await TrailsApi(client, "https://api.example").get_route(identifier(99))


@pytest.mark.parametrize("status", [202, 204, 400, 401, 404, 422, 500, 503, 504])
async def test_unexpected_ingestion_status_never_becomes_success_or_no_route(status):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(status, json=problem()),
    )) as client:
        with pytest.raises(HandoffError) as error:
            await TrailsApi(client, "https://api.example").ingest(candidate())
    assert error.value.status_code == (status if status in (503, 504) else 502)


async def test_saved_route_retains_licensed_photo_fields_and_units():
    payload = route([place()])
    photo = {"url": "https://photo.example/full.jpg", "thumbUrl": "https://photo.example/thumb.jpg",
             "author": "Fixture author", "license": "CC BY-SA 4.0",
             "sourceUrl": "https://photo.example/attribution", "lat": 49.1, "lon": 20.1}
    payload["places"][0]["photos"] = [photo]
    payload["segments"] = [{"fromKm": 0, "toKm": 7.5, "photos": [photo]}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=payload),
    )) as client:
        saved = await TrailsApi(client, "https://api.example").get_route(identifier(99))
    assert saved.model_dump(mode="json") == payload


async def test_route_identifier_remains_an_opaque_string_and_is_encoded_in_the_path():
    payload = route()
    payload["id"] = "saved/route?fixture"

    def handle(request):
        assert request.url.raw_path == b"/api/routes/saved%2Froute%3Ffixture"
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        saved = await TrailsApi(client, "https://api.example").get_route(payload["id"])
    assert saved.id == payload["id"]
