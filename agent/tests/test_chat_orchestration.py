import asyncio
import json
import logging
from unittest.mock import AsyncMock, Mock

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from gopstop_agent.chat import ChatService
from gopstop_agent.config import Settings
from gopstop_agent.handoff import HandoffResult
from gopstop_agent.intent import IntentClarificationRequired, ProviderError, ProviderTimeout
from gopstop_agent.main import create_app
from gopstop_agent.trails_api import HandoffError, NoHikingRoute
from test_discovery import provider_fixture, row, tool
from test_handoff import ApiFixture, discovery
from test_trails_api import place, route


@pytest.fixture
async def build_app():
    resources = []

    def build(handler=None, service=None, **overrides):
        cache = fakeredis.aioredis.FakeRedis(decode_responses=True)
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler or (lambda _: httpx.Response(500))))
        settings = Settings(_env_file=None,
                            nominatim_user_agent="TrailsTest/1.0 team@example.org", api_base_url="https://api.example",
                            **{"chat_enabled": True, "anthropic_api_key": "fixture-claude-secret",
                               "exa_api_key": "fixture-exa-secret", **overrides})
        app = create_app(settings, cache, http, service)
        resources.append((http, cache))
        return app, cache, http

    yield build
    for http, cache in resources:
        await http.aclose()
        await cache.aclose()


@pytest.mark.parametrize("provider", ["anthropic", "groq"])
async def test_http_factories_preserve_sources_history_and_saved_route_with_safe_stage_logs(build_app, caplog, provider):
    api, provider_calls, reply_calls = ApiFixture(), [], []
    intent = {"start": "Štrbské Pleso", "end": "Rysy", "mustSee": ["Skok"], "preferences": ["wild scenery"]}
    places = {name: (name, [row(i, name, 49 + i / 1000, 20 + i / 1000)])
              for i, name in enumerate(("Štrbské Pleso", "Skok", "Rysy"), 1)}
    providers = provider_fixture(intent, places, provider_calls)

    def handle(request):
        if request.url.host == "api.example":
            return api(request)
        body = json.loads(request.content) if request.content else {}
        if request.url.host == "api.groq.com":
            assert provider == "groq" and request.headers["Authorization"] == "Bearer fixture-groq-secret"
            assert body["model"] == "openai/gpt-oss-120b"
            name = body["tool_choice"]["function"]["name"]
            adapted = httpx.Request("POST", "https://api.anthropic.com/v1/messages", json={
                "tool_choice": {"name": name}, "messages": body["messages"][1:],
            })
            result = handle(adapted).json()["content"][0]["input"]
            return httpx.Response(200, json={"choices": [{"finish_reason": "tool_calls", "message": {
                "tool_calls": [{"type": "function", "function": {"name": name, "arguments": json.dumps(result)}}],
            }}]})
        if body.get("tool_choice", {}).get("name") == "write_chat_reply":
            reply_calls.append(json.loads(body["messages"][0]["content"]))
            return tool("write_chat_reply", {"reply": "Маршрут через водопад готов."})
        return providers(request)

    app, cache, http = build_app(handle, llm_provider=provider, groq_api_key="fixture-groq-secret",
                                 anthropic_api_key="" if provider == "groq" else "fixture-claude-secret")
    with caplog.at_level(logging.INFO, logger="gopstop_agent.diagnostics"), TestClient(app) as client:
        for message in ("Хочу маршрут через Skok", "Оставь тот же водопад"):
            response = client.post("/api/chat", headers={"Origin": "http://localhost:5173"},
                                   json={"sessionId": "private-session", "message": message})
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
            body = response.json()
            assert set(body) == {"reply", "places", "routeId"}
            assert body["reply"] == "Маршрут через водопад готов."
            assert [p["source"] for p in body["places"]] == [f"https://evidence.example/{i}" for i in range(3)]
            assert body["routeId"] == api.saved_route["id"]
    assert not http.is_closed  # The caller owns injected clients.
    stored = [json.loads(item) for item in await cache.lrange("gopstop:chat-session:private-session", 0, -1)]
    assert len(stored) == 4 and reply_calls[1]["history"] == stored[:2]
    extraction = [json.loads(r.content) for r in provider_calls if r.content
                  and json.loads(r.content).get("tool_choice", {}).get("name") == "extract_route_intent"]
    assert extraction[1]["messages"][:-1] == stored[:2]
    assert sum(r.url.host == "api.exa.ai" for r in provider_calls) == 3  # Cached on follow-up.
    resolution = [r for r in provider_calls if r.content
                  and json.loads(r.content).get("tool_choice", {}).get("name") == "resolve_place"]
    assert len(resolution) == 3  # Intent and reply remain per-message; resolution is reused.
    for stage in ("history", "intent", "research", "resolution", "geocoding", "ingestion",
                  "routing_cache", "route_readback", "reply", "session_save"):
        assert f"stage={stage}" in caplog.text
    assert "private-session" not in caplog.text and "fixture-claude-secret" not in caplog.text


@pytest.mark.parametrize("operation", ["get", "set"])
async def test_resolution_cache_failure_returns_safe_503_without_ingestion_or_exchange(build_app, monkeypatch, operation):
    api, calls = ApiFixture(), []
    providers = provider_fixture({"start": "Skok", "end": "Skok"},
                                 {"Skok": ("Skok", [row(1, "Skok", 49.14, 20.05)])}, calls)

    def handle(request):
        return api(request) if request.url.host == "api.example" else providers(request)

    app, cache, _ = build_app(handle)
    original = getattr(cache, operation)

    async def fail_resolution_cache(key, *args, **kwargs):
        if key.startswith("gopstop:place-resolution:"):
            raise RedisError("private cache credentials")
        return await original(key, *args, **kwargs)

    monkeypatch.setattr(cache, operation, fail_resolution_cache)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"sessionId": "cache-failure", "message": "Find Skok"})
    assert response.status_code == 503 and "private" not in response.text
    assert response.json() == {"detail": "Place research cache is temporarily unavailable."}
    assert api.calls == [] and await cache.llen("gopstop:chat-session:cache-failure") == 0
    resolution = [r for r in calls if r.content
                  and json.loads(r.content).get("tool_choice", {}).get("name") == "resolve_place"]
    assert len(resolution) == (0 if operation == "get" else 1)


def service_for(finding=None, extraction_error=None, handoff_error=None):
    search, handoff, replies = AsyncMock(), AsyncMock(), AsyncMock()
    search.discover.return_value = finding or discovery()
    search.discover.side_effect = extraction_error
    handoff.persist.return_value = HandoffResult.model_validate_json(json.dumps({
        "route": route([place(2)]), "places": [place(1), place(2), place(3)], "attribution": "OSM",
    }))
    handoff.persist.side_effect = handoff_error
    replies.write.return_value = "Уточните маршрут."
    return ChatService(search, handoff, replies), search, handoff, replies


@pytest.mark.parametrize("kind", ["missing", "ambiguous", "limits", "no_route"])
async def test_normal_clarifications_and_no_route_store_exchange_without_route_id(build_app, kind):
    finding = discovery()
    if kind == "missing":
        finding.intent.end = None
    if kind == "ambiguous":
        finding.stops[0].place = None
    service, _, handoff, replies = service_for(
        finding, IntentClarificationRequired("Choose at most five stops.") if kind == "limits" else None,
        NoHikingRoute() if kind == "no_route" else None,
    )
    app, cache, _ = build_app(service=service)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"sessionId": "clarify", "message": "Помоги с маршрутом"})
    assert response.status_code == 200 and response.json() == {"reply": "Уточните маршрут.", "places": []}
    assert await cache.llen("gopstop:chat-session:clarify") == 2
    assert replies.write.call_args.args[2] == ("no_route" if kind == "no_route" else "clarification")
    if kind != "no_route":
        handoff.persist.assert_not_awaited()


@pytest.mark.parametrize("failure,status", [(ProviderError("private"), 502), (ProviderTimeout("private"), 504),
                                          (RedisError("private"), 503), (HandoffError("Safe API failure", 503), 503)])
async def test_dependency_failure_never_records_success(build_app, failure, status):
    service, _, handoff, replies = service_for(
        handoff_error=failure if isinstance(failure, HandoffError) else None,
        extraction_error=None if isinstance(failure, HandoffError) else failure,
    )
    app, cache, _ = build_app(service=service)
    with TestClient(app) as client:
        response = client.post("/api/chat", headers={"Origin": "http://localhost:5173"},
                               json={"sessionId": "failed", "message": "Find Skok"})
    assert response.status_code == status and "private" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert await cache.llen("gopstop:chat-session:failed") == 0
    if not isinstance(failure, HandoffError):
        handoff.persist.assert_not_awaited()
    replies.write.assert_not_awaited()


@pytest.mark.parametrize("phase", ["reply", "session_save"])
async def test_failure_after_route_creation_returns_error_without_claiming_saved_exchange(build_app, phase):
    service, _, handoff, replies = service_for()
    if phase == "reply":
        replies.write.side_effect = ProviderError("private")
    app, cache, _ = build_app(service=service)
    with TestClient(app) as client:
        if phase == "session_save":
            app.state.session_store.record_exchange = AsyncMock(side_effect=RedisError("private"))
        response = client.post("/api/chat", json={"sessionId": "failed", "message": "Find Skok"})
    assert response.status_code == (502 if phase == "reply" else 503)
    assert await cache.llen("gopstop:chat-session:failed") == 0
    handoff.persist.assert_awaited_once()  # The API may already have committed data.


@pytest.mark.parametrize("phase", ["history", "discovery", "handoff", "reply", "session_save"])
async def test_total_deadline_covers_all_async_stages_and_cancels_work(build_app, phase):
    stopped = asyncio.Event()

    async def stall(*_):
        try:
            await asyncio.sleep(10)
        finally:
            stopped.set()

    service, search, handoff, replies = service_for()
    target = {"discovery": search.discover, "handoff": handoff.persist, "reply": replies.write}.get(phase)
    if target is not None:
        target.side_effect = stall
    app, cache, _ = build_app(service=service, chat_timeout_seconds=0.02)
    with TestClient(app) as client:
        if phase in ("history", "session_save"):
            setattr(app.state.session_store, phase if phase == "history" else "record_exchange", AsyncMock(side_effect=stall))
        response = client.post("/api/chat", json={"sessionId": "deadline", "message": "Find Skok"})
    assert response.status_code == 504 and stopped.is_set()
    assert await cache.llen("gopstop:chat-session:deadline") == 0


@pytest.mark.parametrize("value", ["not-json", "[]", '{"role":"system","content":"private"}',
                                  '{"role":"user","content":1}', '{"role":"user","content":" "}',
                                  json.dumps({"role": "user", "content": "x" * 4001})])
async def test_corrupt_history_stops_before_paid_work(build_app, value):
    service, search, _, _ = service_for()
    app, cache, _ = build_app(service=service)
    await cache.rpush("gopstop:chat-session:broken", value)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"sessionId": "broken", "message": "Find Skok"})
    assert response.status_code == 503
    search.discover.assert_not_awaited()


@pytest.mark.parametrize("provider,key,model", [("anthropic", "anthropic_api_key", "anthropic_model"),
                                              ("groq", "groq_api_key", "groq_model")])
@pytest.mark.parametrize("missing", ["key", "exa", "model"])
def test_enabled_production_factory_rejects_missing_keys_before_resources(monkeypatch, provider, key, model, missing):
    import gopstop_agent.main as main
    factory = Mock()
    monkeypatch.setattr(main, "from_url", factory)
    values = {"llm_provider": provider, key: "fixture", "exa_api_key": "fixture", model: "model",
              {"key": key, "exa": "exa_api_key", "model": model}[missing]: " "}
    with pytest.raises(ValueError, match="requires the selected LLM key"):
        with TestClient(create_app(Settings(_env_file=None, chat_enabled=True, **values))):
            pass
    factory.assert_not_called()


@pytest.mark.parametrize("startup_failure", [False, True])
async def test_disabled_mode_has_no_provider_calls_and_owned_resources_close(build_app, monkeypatch, startup_failure):
    import gopstop_agent.main as main
    app, _, injected = build_app(chat_enabled=False)
    with TestClient(app) as client:
        assert client.post("/api/chat", json={"sessionId": "s", "message": "Hi"}).json()["places"] == []
    assert not injected.is_closed
    owned_http = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    owned_cache = fakeredis.aioredis.FakeRedis(decode_responses=True)
    close = AsyncMock(wraps=owned_cache.aclose)
    monkeypatch.setattr(owned_cache, "aclose", close)
    monkeypatch.setattr(main, "from_url", lambda *_, **__: owned_cache)
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **_: owned_http)
    if startup_failure:
        monkeypatch.setattr(main, "create_chat", Mock(side_effect=ValueError("factory failed")))
    app = create_app(Settings(_env_file=None, chat_enabled=True, anthropic_api_key="fixture", exa_api_key="fixture"))
    if startup_failure:
        with pytest.raises(ValueError, match="factory failed"):
            with TestClient(app):
                pass
    else:
        with TestClient(app):
            pass
    assert owned_http.is_closed
    close.assert_awaited_once()
