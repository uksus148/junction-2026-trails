import asyncio
import json

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

from gopstop_agent.config import Settings
from gopstop_agent.main import create_app


def settings(**overrides):
    return Settings(enable_discovery=True, anthropic_api_key="fixture", exa_api_key="fixture",
                    **overrides)


def tool(name, value):
    return httpx.Response(200, json={"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "name": name, "input": value,
    }]})


def provider_fixture(intent, locations, calls):
    def handle(request):
        calls.append(request)
        body = json.loads(request.content) if request.content else {}
        if request.url.host == "api.anthropic.com":
            name = body["tool_choice"]["name"]
            if name == "extract_route_intent":
                return tool(name, intent)
            evidence = json.loads(body["messages"][0]["content"])
            place_name = evidence["sources"][0]["title"]
            return tool(name, {"place": {"name": place_name, "geocodeQuery": place_name,
                                         "sourceIndex": 0, "tags": []}})
        if request.url.host == "api.exa.ai":
            place_name = body["query"].split(". Hiking")[0]
            return httpx.Response(200, json={"results": [{
                "title": place_name, "url": f"https://example.org/source/{list(locations).index(place_name)}",
                "text": "Fixture research evidence",
            }]})
        assert request.url.host == "nominatim.openstreetmap.org"
        location = locations[request.url.params["q"]]
        return httpx.Response(200, json=[] if location is None else [{
            "osm_type": "node", "osm_id": list(locations).index(request.url.params["q"]) + 1,
            "display_name": request.url.params["q"], "lat": location[0], "lon": location[1],
        }])
    return handle


async def test_tatras_chat_returns_sourced_places_caches_and_reuses_history():
    intent = {"start": "Štrbské Pleso", "end": "Rysy", "mustSee": ["Skok waterfall"],
              "preferences": ["wild scenery"]}
    locations = {"Štrbské Pleso": (49.119, 20.063), "Skok waterfall": (49.166, 20.061),
                 "Rysy": (49.179, 20.088)}
    calls = []
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider_fixture(intent, locations, calls))) as web:
        with TestClient(create_app(settings(), redis, web)) as client:
            for message in ["Hike from Štrbské Pleso to Rysy via Skok waterfall. I love wild scenery.",
                            "Keep that route, please."]:
                response = client.post("/api/chat", json={"sessionId": "demo", "message": message})
                assert response.status_code == 200, response.text
                body = response.json()
                assert set(body) == {"reply", "places"}
                assert [p["name"] for p in body["places"]] == list(locations)
                assert [p["id"] for p in body["places"]] == ["osm:node:1", "osm:node:2", "osm:node:3"]
                assert all(p["source"].startswith("https://example.org/source/") for p in body["places"])
                assert body["places"][1]["lat"] == 49.166
                assert body["places"][1]["lon"] == 20.061
                assert "route has not been built" in body["reply"]
                assert "OpenStreetMap" in body["reply"]
    assert sum(r.url.host == "api.exa.ai" for r in calls) == 3
    assert sum(r.url.host == "nominatim.openstreetmap.org" for r in calls) == 3
    extraction = [json.loads(r.content) for r in calls if r.url.host == "api.anthropic.com"
                  and json.loads(r.content)["tool_choice"]["name"] == "extract_route_intent"]
    assert len(extraction[1]["messages"]) == 3
    assert await redis.llen("gopstop:chat-session:demo") == 4
    await redis.aclose()


async def test_chat_accepts_other_regions_and_reports_unresolved_places():
    intent = {"start": "Tromsø", "end": "Fløya", "mustSee": [], "preferences": []}
    locations = {"Tromsø": (69.65, 18.96), "Fløya": None}
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider_fixture(intent, locations, []))) as web:
        with TestClient(create_app(settings(), redis, web)) as client:
            response = client.post("/api/chat", json={"sessionId": "norway", "message": "Hike in Tromsø"})
    assert response.status_code == 200
    assert [p["name"] for p in response.json()["places"]] == ["Tromsø"]
    assert "more specific location for: Fløya" in response.json()["reply"]
    await redis.aclose()


async def test_provider_error_returns_503_without_saving_a_successful_exchange():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(429, json={"error": "private upstream details"}),
    )) as web:
        with TestClient(create_app(settings(), redis, web)) as client:
            response = client.post("/api/chat", headers={"Origin": "http://localhost:5173"},
                                   json={"sessionId": "failed", "message": "Hike to Skok"})
    assert response.status_code == 503
    assert "private" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert await redis.llen("gopstop:chat-session:failed") == 0
    await redis.aclose()


def test_overall_chat_deadline_cancels_discovery():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app = create_app(settings(chat_timeout_seconds=0.02), redis)
    with TestClient(app) as client:
        async def stall(*_):
            await asyncio.sleep(10)
        app.state.discovery.respond = stall
        response = client.post("/api/chat", json={"sessionId": "deadline", "message": "Find Skok"})
    assert response.status_code == 503


def test_live_discovery_requires_keys():
    with pytest.raises(ValueError, match="requires ANTHROPIC_API_KEY and EXA_API_KEY"):
        create_app(Settings(enable_discovery=True, anthropic_api_key="", exa_api_key=""))
