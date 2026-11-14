"""Discover sourced route candidates; API persistence is a separate boundary."""

import asyncio

import httpx
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from gopstop_agent.config import Settings
from gopstop_agent.exa import ExaSearch, ResearchSource
from gopstop_agent.geocoding import GeocodedPlace, NominatimGeocoder, OSM_ATTRIBUTION
from gopstop_agent.intent import ClaudeIntentExtractor, Message, ProviderError, RouteIntent
from gopstop_agent.resolver import ClaudePlaceResolver


class DiscoveredPlace(BaseModel):
    name: str
    tags: list[str]
    source: ResearchSource
    location: GeocodedPlace


class PlaceFinding(BaseModel):
    description: str
    sources: list[ResearchSource]
    place: DiscoveredPlace | None = None


class DiscoveryResult(BaseModel):
    intent: RouteIntent
    start: PlaceFinding | None = None
    stops: list[PlaceFinding] = Field(default_factory=list)
    end: PlaceFinding | None = None
    attribution: str = OSM_ATTRIBUTION

    @property
    def unresolved(self) -> list[str]:
        return [finding.description for finding in [self.start, *self.stops, self.end]
                if finding is not None and finding.place is None]

    @property
    def missing_endpoints(self) -> list[str]:
        return [name for name in ("start", "end") if getattr(self.intent, name) is None]

    @property
    def ready_for_handoff(self) -> bool:
        return not self.missing_endpoints and bool(self.start and self.start.place and self.end and self.end.place
                    and all(finding.place is not None for finding in self.stops))


class PlaceDiscovery:
    def __init__(self, intent: ClaudeIntentExtractor, search: ExaSearch,
                 resolver: ClaudePlaceResolver, geocoder: NominatimGeocoder,
                 timeout_seconds: float = 60) -> None:
        self._intent, self._search, self._resolver, self._geocoder = intent, search, resolver, geocoder
        self._timeout_seconds = timeout_seconds

    async def discover(self, message: str, history: list[Message]) -> DiscoveryResult:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                intent = await self._intent.extract(message, history)
                found: dict[str, PlaceFinding] = {}

                async def find(description: str) -> PlaceFinding:
                    if description in found:
                        return found[description]
                    query = (f"Find hiking place: {description}. Route context: "
                             f"{intent.start or 'unspecified'} to {intent.end or 'unspecified'}.")
                    sources = await self._search.search(query)
                    finding = PlaceFinding(description=description, sources=sources)
                    resolution = await self._resolver.resolve(query, sources)
                    if resolution is not None:
                        location = await self._geocoder.geocode(resolution.geocodeQuery)
                        if location is not None:
                            finding.place = DiscoveredPlace(
                                name=resolution.name, tags=resolution.tags,
                                source=sources[resolution.sourceIndex], location=location,
                            )
                    found[description] = finding
                    return finding

                start = await find(intent.start) if intent.start is not None else None
                stops = [await find(description) for description in intent.mustSee]
                end = await find(intent.end) if intent.end is not None else None
                return DiscoveryResult(intent=intent, start=start, stops=stops, end=end)
        except TimeoutError as exc:
            raise ProviderError("Place discovery exceeded its time limit.") from exc


def create_discovery(client: httpx.AsyncClient, cache: Redis, settings: Settings) -> PlaceDiscovery:
    """Build during startup when live discovery is enabled by a future caller."""
    claude_key = settings.anthropic_api_key.get_secret_value()
    exa_key = settings.exa_api_key.get_secret_value()
    if not claude_key or not exa_key:
        raise ValueError("Place discovery requires ANTHROPIC_API_KEY and EXA_API_KEY.")
    timeout = settings.provider_timeout_seconds
    return PlaceDiscovery(
        ClaudeIntentExtractor(client, claude_key, settings.anthropic_model, timeout),
        ExaSearch(client, cache, exa_key, timeout),
        ClaudePlaceResolver(client, claude_key, settings.anthropic_model, timeout),
        NominatimGeocoder(client, cache, settings.nominatim_user_agent,
                          str(settings.nominatim_base_url), timeout),
        settings.discovery_timeout_seconds,
    )
