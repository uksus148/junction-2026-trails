"""Compose existing discovery/handoff and language-aware replies."""

import httpx
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from gopstop_agent.api_models import ApiPlace
from gopstop_agent.config import Settings
from gopstop_agent.diagnostics import stage
from gopstop_agent.discovery import PlaceDiscovery, create_discovery
from gopstop_agent.handoff import RouteHandoff, create_handoff
from gopstop_agent.intent import IntentClarificationRequired, Message
from gopstop_agent.replies import ClaudeReplyWriter
from gopstop_agent.trails_api import HandoffError, NoHikingRoute


class ChatResponse(BaseModel):
    reply: str
    places: list[ApiPlace]
    routeId: str | None = None


class ChatService:
    def __init__(self, discovery: PlaceDiscovery, handoff: RouteHandoff,
                 replies: ClaudeReplyWriter) -> None:
        self._discovery, self._handoff, self._replies = discovery, handoff, replies

    async def respond(self, message: str, history: list[Message]) -> ChatResponse:
        places, route_id = [], None
        try:
            with stage("discovery"):
                finding = await self._discovery.discover(message, history)
        except IntentClarificationRequired as exc:
            outcome, facts = "clarification", {"question": exc.question}
        except RedisError as exc:
            raise HandoffError("Place research cache is temporarily unavailable.", 503) from exc
        else:
            if not finding.ready_for_handoff:
                outcome, facts = "clarification", {
                    "missingEndpoints": finding.missing_endpoints, "unresolvedPlaces": finding.unresolved,
                }
            else:
                try:
                    with stage("handoff"):
                        saved = await self._handoff.persist(finding)
                except NoHikingRoute:
                    outcome, facts = "no_route", {"question": "Please choose different endpoints or stops."}
                else:
                    outcome, facts = "ready", {
                        "places": [place.name for place in saved.places],
                        "intermediateStops": [place.name for place in saved.route.places],
                        "distanceKm": saved.route.distanceKm, "ascentM": saved.route.ascentM,
                        "durationMin": saved.route.durationMin,
                    }
                    places, route_id = saved.places, saved.route.id
        with stage("reply"):
            reply = await self._replies.write(message, history, outcome, facts)
        return ChatResponse(reply=reply, places=places, routeId=route_id)


def create_chat(client: httpx.AsyncClient, cache: Redis, settings: Settings) -> ChatService:
    return ChatService(create_discovery(client, cache, settings), create_handoff(client, settings),
                       ClaudeReplyWriter(client, settings.anthropic_api_key.get_secret_value(),
                                         settings.anthropic_model, settings.provider_timeout_seconds))
