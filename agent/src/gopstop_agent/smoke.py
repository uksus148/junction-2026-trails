"""Explicit live preflight / HTTP end-to-end check; never runs in normal pytest."""

import argparse
import asyncio
import hashlib
import json
import time
from uuid import uuid4

import httpx
from pydantic import TypeAdapter
from redis.asyncio import from_url
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from gopstop_agent.chat import ChatResponse
from gopstop_agent.api_models import ApiPlace
from gopstop_agent.config import Settings
from gopstop_agent.exa import ExaSearch
from gopstop_agent.geocoding import NominatimGeocoder
from gopstop_agent.intent import ClaudeIntentExtractor
from gopstop_agent.llm import create_tool_model
from gopstop_agent.replies import ClaudeReplyWriter
from gopstop_agent.resolver import ClaudePlaceResolver
from gopstop_agent.sessions import ValkeySessionStore
from gopstop_agent.trails_api import HandoffError, TrailsApi, url_adapter


MESSAGE = "Hike from Štrbské Pleso railway station to Popradské Pleso railway station in Slovakia."


def require(condition) -> None:
    if not condition:
        raise ValueError("Live check did not satisfy its acceptance condition.")


async def preflight(http, cache, settings: Settings, report: dict) -> None:
    settings.require_chat_configuration()
    report["stage"] = "session_storage"
    session = f"preflight-{uuid4().hex}"
    store = ValkeySessionStore(cache, 60, 2)
    try:
        await store.record_exchange(session, "Preflight", "Storage check")
        require(len(await store.history(session)) == 2)
    finally:
        await cache.delete(store._key(session))  # Only this check's unique key.
    report["checks"].append("session_storage")
    model = create_tool_model(http, settings)
    key, name, timeout = settings.llm_key.get_secret_value(), settings.llm_model, settings.provider_timeout_seconds
    report["stage"] = "llm_intent"
    intent = await ClaudeIntentExtractor(http, key, name, timeout, tool_model=model).extract(MESSAGE, [])
    require(intent.start and intent.end)
    report["checks"].append("llm_intent")
    report["stage"] = "exa"
    namespace = f"gopstop:preflight:exa:{uuid4().hex}"
    try:
        # A previous shared cache hit must not falsely validate a new Exa key.
        sources = await ExaSearch(http, cache, settings.exa_api_key.get_secret_value(), timeout,
                                  cache_namespace=namespace).search("Skok waterfall High Tatras Slovakia hiking")
    finally:
        async for key_name in cache.scan_iter(match=namespace + ":*"):
            await cache.delete(key_name)
    require(sources)
    report["checks"].append("exa")
    report["stage"] = "llm_resolution"
    place = await ClaudePlaceResolver(http, key, name, timeout, tool_model=model).resolve("Skok waterfall", sources)
    report["checks"].append("llm_resolution")
    report["stage"] = "nominatim"
    location = await NominatimGeocoder(http, cache, settings.nominatim_user_agent,
                                     str(settings.nominatim_base_url), timeout).geocode(
        place.geocodeQuery if place else "Skok waterfall, Slovakia",
    )
    report["geocoding"] = "resolved" if location else "needs_clarification"
    report["checks"].append("nominatim")
    report["stage"] = "llm_reply"
    await ClaudeReplyWriter(http, key, name, timeout, tool_model=model).write(
        "Help me choose a hike.", [], "clarification", {"missingEndpoints": ["start", "end"]},
    )
    report["checks"].append("llm_reply")
    report["stage"] = "api_read"
    response = await http.get(str(settings.api_base_url).rstrip("/") + "/api/places",
                              params={"bbox": "20,49,21,50"}, timeout=settings.api_timeout_seconds)
    response.raise_for_status()
    TypeAdapter(list[ApiPlace]).validate_json(response.content)
    report["checks"].append("api_read")  # Read-only access does not prove V3 deployment.


async def chat_smoke(http, cache, settings: Settings, agent_url: str, message: str, report: dict) -> None:
    if not settings.chat_enabled:
        raise ValueError("Chat smoke requires explicitly enabled chat after E4.")
    session = f"e2e-{uuid4().hex}"
    report["sessionHash"] = hashlib.sha256(session.encode()).hexdigest()[:12]
    report["stage"] = "cors"
    origin = settings.cors_origins[0]
    options = await http.options(agent_url.rstrip("/") + "/api/chat", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type",
    }, timeout=settings.api_timeout_seconds)
    options.raise_for_status()
    require(options.headers.get("access-control-allow-origin") == origin)
    require("POST" in [v.strip().upper() for v in options.headers.get("access-control-allow-methods", "").split(",")])
    require("content-type" in [v.strip().lower() for v in options.headers.get("access-control-allow-headers", "").split(",")])
    report["stage"] = "chat"
    response = await http.post(agent_url.rstrip("/") + "/api/chat",
                               json={"sessionId": session, "message": message},
                               headers={"Origin": origin},
                               timeout=settings.chat_timeout_seconds + 5, follow_redirects=False)
    response.raise_for_status()
    require(response.headers.get("access-control-allow-origin") == origin)
    chat = ChatResponse.model_validate_json(response.content)
    if not chat.routeId:
        raise ValueError("Clarification/no-route is valid chat, but not a completed route smoke.")
    report["stage"] = "route_readback"
    route = await TrailsApi(http, str(settings.api_base_url), settings.api_timeout_seconds).get_route(chat.routeId)
    canonical = {place.id: place for place in chat.places}
    require(len(canonical) == len(chat.places) and chat.places)
    for visit in route.places:
        require(visit.model_dump(exclude={"photos"}) == canonical[visit.id].model_dump(exclude={"photos"}))
    for place in chat.places:
        url_adapter.validate_python(place.source)
    report["stage"] = "session_readback"
    history = await ValkeySessionStore(cache, settings.session_ttl_seconds, settings.session_max_messages).history(session)
    require(history[-2:] == [{"role": "user", "content": message}, {"role": "assistant", "content": chat.reply}])
    report.update(routeId=route.id, placeIds=[str(p.id) for p in chat.places],
                  checks=["cors", "chat", "route_readback", "session_readback"])
    # Keep saved route/places and the expiring exchange as acceptance evidence; no POST replay/rollback.


async def run(args) -> int:
    report = {"status": "failed", "stage": "configuration", "checks": []}
    started = time.monotonic()
    try:
        settings = Settings()
        report.update(configuredProvider=settings.llm_provider, model=settings.llm_model)
        settings.require_chat_configuration()
        async with asyncio.timeout(settings.chat_timeout_seconds + 10):
            async with httpx.AsyncClient(follow_redirects=False) as http, from_url(
                str(settings.valkey_url), decode_responses=True,
                socket_connect_timeout=settings.valkey_connect_timeout_seconds,
                socket_timeout=settings.valkey_socket_timeout_seconds, retry=Retry(NoBackoff(), 0),
            ) as cache:
                if args.chat:
                    await chat_smoke(http, cache, settings, args.agent_url, args.message, report)
                else:
                    await preflight(http, cache, settings, report)
        report.update(status="passed", stage="complete")
    except Exception as exc:
        report["error"] = type(exc).__name__  # No provider bodies, messages, URLs or credentials.
        cause = exc.__cause__ or exc
        if isinstance(cause, httpx.HTTPStatusError):
            report["httpStatus"] = cause.response.status_code
        elif isinstance(exc, HandoffError):
            report["httpStatus"] = exc.status_code
    report["elapsedMs"] = round((time.monotonic() - started) * 1000)
    print(json.dumps(report))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chat", action="store_true", help="Create a real route; run only after reviewed E4.")
    parser.add_argument("--agent-url", default="http://localhost:8000")
    parser.add_argument("--message", default=MESSAGE)
    raise SystemExit(asyncio.run(run(parser.parse_args())))
