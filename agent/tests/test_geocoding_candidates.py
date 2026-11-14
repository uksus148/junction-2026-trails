import json

import fakeredis.aioredis
import httpx
import pytest

from gopstop_agent.geocoding import GeocodedPlace, NominatimGeocoder
from gopstop_agent.geocoding_candidates import GeocodingCandidate, select_candidate
from gopstop_agent.intent import ProviderError


# Reduced public Nominatim responses observed on November 14; OSM attribution
# https://www.openstreetmap.org/copyright. No live request is made by these tests.
SKOK = {"osm_type": "node", "osm_id": 383862401, "name": "Vodopád Skok",
        "display_name": "Vodopád Skok, Štrba, Slovakia", "type": "waterfall",
        "lat": "49.1531240", "lon": "20.0452686"}
WESTERN_SKOK = {**SKOK, "osm_id": 10923822165, "name": "Skok", "display_name": "Skok, Jalovec, Slovakia",
                "lat": "49.1642352", "lon": "19.6563730"}
RYSY = {"osm_type": "node", "osm_id": 1862536196, "name": "Rysy", "display_name": "Rysy, Slovakia",
        "type": "peak", "lat": "49.1793186", "lon": "20.0884638"}
LAKE = {"osm_type": "way", "osm_id": 4816134, "name": "Štrbské pleso", "display_name": "Štrbské pleso, Slovakia",
        "type": "lake", "lat": "49.1222049", "lon": "20.0577798"}
RESORT = {**LAKE, "osm_id": 190876251, "type": "winter_sports", "lat": "49.1295731", "lon": "20.0539628"}
MUNICIPALITY = {**LAKE, "osm_type": "relation", "osm_id": 5988018, "name": "Štrba - Štrbské pleso",
                "namedetails": {"_place_name": "Štrbské Pleso"}, "type": "administrative"}


def choose(rows, name="Skok waterfall", tags=None, anchors=None):
    return select_candidate([GeocodingCandidate.model_validate(row) for row in rows],
                            name, tags or [], anchors or [])


@pytest.mark.parametrize("rows", [[WESTERN_SKOK, SKOK], [SKOK, WESTERN_SKOK]])
def test_skok_names_and_types_alone_do_not_justify_picking_the_first_waterfall(rows):
    assert choose(rows, tags=["waterfall"]) is None
    selected = choose(rows, tags=["waterfall"], anchors=[GeocodedPlace.model_validate(RYSY)])
    assert selected.osm_id == SKOK["osm_id"]
    assert (selected.lat, selected.lon) == (49.1531240, 20.0452686)


@pytest.mark.parametrize("tag,expected", [("lake", LAKE), ("resort", RESORT)])
def test_place_type_disambiguates_lake_resort_and_municipality(tag, expected):
    selected = choose([MUNICIPALITY, RESORT, LAKE], "Štrbské Pleso", [tag])
    assert (selected.osm_type, selected.osm_id) == (expected["osm_type"], expected["osm_id"])
    assert choose([MUNICIPALITY, RESORT, LAKE], "Štrbské Pleso") is None


def test_local_ambiguity_conflicting_type_and_unrelated_name_stay_unresolved():
    anchor = GeocodedPlace.model_validate(RYSY)
    assert choose([SKOK, {**SKOK, "osm_id": 2}], tags=["waterfall"], anchors=[anchor]) is None
    assert choose([SKOK], tags=["peak"]) is None
    assert choose([RYSY], tags=["waterfall"]) is None
    assert choose([SKOK], name="???") is None
    assert choose([SKOK, {**SKOK, "lat": "49.5"}], tags=["waterfall"]) is None
    assert choose([WESTERN_SKOK, {**WESTERN_SKOK, "osm_id": 3}], tags=["waterfall"], anchors=[anchor]) is None


def test_aliases_diacritics_and_repeated_identity_do_not_create_false_ambiguity():
    assert choose([LAKE], "Strba Tarn", ["lake"]) is None
    row = {**LAKE, "namedetails": {"name:en": "Štrba Tarn", "alt_name:en": "Lake Štrba;Other lake"}}
    assert choose([row, row], "Strba Tarn", ["lake"]).osm_id == LAKE["osm_id"]


async def test_empty_region_query_falls_back_once_and_reuses_candidates_for_new_context():
    queries = []

    def handle(request):
        queries.append(request.url.params["q"])
        return httpx.Response(200, json=[] if len(queries) == 1 else [WESTERN_SKOK, SKOK])

    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as cache, httpx.AsyncClient(
        transport=httpx.MockTransport(handle),
    ) as client:
        # Ignore the old 24h null decision without deleting team data.
        await cache.set("gopstop:nominatim:result:v1:old", "null", ex=86400)
        geocoder = NominatimGeocoder(client, cache, "Fixture/1.0")
        query = "Skok waterfall, High Tatras, Slovakia"
        assert await geocoder.geocode(query, name="Skok waterfall", tags=["waterfall"]) is None
        assert (await geocoder.geocode(query, name="Skok waterfall", tags=["waterfall"],
                                      anchors=[GeocodedPlace.model_validate(RYSY)])).osm_id == SKOK["osm_id"]
        assert await geocoder.geocode(query, name="Skok waterfall", tags=["peak"]) is None
        assert queries == [query, "Skok waterfall, Slovakia"]
        keys = await cache.keys("gopstop:nominatim:search:v2:*")
        for key in keys:
            value = json.loads(await cache.get(key))
            assert isinstance(value, list)
            assert 0 < await cache.ttl(key) <= (86400 if value else 300)
        assert await cache.get("gopstop:nominatim:result:v1:old") == "null"


@pytest.mark.parametrize("rows", [[WESTERN_SKOK, SKOK], "error"])
async def test_ambiguity_or_http_failure_never_triggers_a_broader_search(rows):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(503) if rows == "error" else httpx.Response(200, json=rows)

    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as cache, httpx.AsyncClient(
        transport=httpx.MockTransport(handle),
    ) as client:
        geocoder = NominatimGeocoder(client, cache, "Fixture/1.0")
        if rows == "error":
            with pytest.raises(ProviderError):
                await geocoder.geocode("Skok waterfall, High Tatras, Slovakia")
            assert not await cache.keys("gopstop:nominatim:search:v2:*")
        else:
            assert await geocoder.geocode("Skok waterfall, High Tatras, Slovakia", tags=["waterfall"]) is None
    assert len(calls) == 1


async def test_corrupt_candidates_refresh_and_empty_search_expires_without_extending_on_hit():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=[])

    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as cache, httpx.AsyncClient(
        transport=httpx.MockTransport(handle),
    ) as client:
        geocoder = NominatimGeocoder(client, cache, "Fixture/1.0")
        assert await geocoder.geocode("unknown") is None
        key, = await cache.keys("gopstop:nominatim:search:v2:*")
        await cache.expire(key, 100)
        assert await geocoder.geocode("unknown") is None
        assert 0 < await cache.ttl(key) <= 100 and len(calls) == 1
        await cache.set(key, "null", ex=300)
        assert await geocoder.geocode("unknown") is None
        assert len(calls) == 2
