"""Persist complete discovery findings, then verify a fetchable saved route."""

import asyncio

import httpx
from pydantic import BaseModel

from gopstop_agent.api_models import ApiPlace, ApiRoute
from gopstop_agent.config import Settings
from gopstop_agent.discovery import DiscoveryResult
from gopstop_agent.trails_api import HandoffError, TrailsApi


class HandoffResult(BaseModel):
    route: ApiRoute
    places: list[ApiPlace]
    attribution: str


class RouteHandoff:
    def __init__(self, api: TrailsApi, timeout_seconds: float = 60) -> None:
        self._api, self._timeout = api, timeout_seconds

    async def persist(self, discovery: DiscoveryResult) -> HandoffResult:
        if not discovery.ready_for_handoff:
            raise ValueError("Resolve every required location before persistence.")
        try:
            async with asyncio.timeout(self._timeout):
                by_osm: dict[tuple[str, int], ApiPlace] = {}
                visits = []
                for finding in [discovery.start, *discovery.stops, discovery.end]:
                    candidate = finding.place
                    key = (candidate.location.osm_type, candidate.location.osm_id)
                    if key not in by_osm:
                        by_osm[key] = await self._api.ingest(candidate)
                    visits.append(by_osm[key])
                stops = visits[1:-1]
                created = await self._api.create_route(visits[0], visits[-1], stops,
                                                       discovery.intent.preferences)
                saved = await self._api.get_route(created.id)
                self._api.check_stops(saved, stops)
                # Deduplicate display records only; the route retains all requested visits.
                unique = {}
                for place in visits:
                    unique.setdefault(place.id, place)
                return HandoffResult(route=saved, places=list(unique.values()),
                                     attribution=discovery.attribution)
        except TimeoutError as exc:
            raise HandoffError("Route handoff exceeded its time limit.", 504) from exc


def create_handoff(client: httpx.AsyncClient, settings: Settings) -> RouteHandoff:
    """Compose explicitly; HTTP chat does not enable this internal client yet."""
    return RouteHandoff(TrailsApi(client, str(settings.api_base_url), settings.api_timeout_seconds),
                        settings.handoff_timeout_seconds)
