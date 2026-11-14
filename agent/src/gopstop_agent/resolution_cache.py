"""Reuse source-grounded resolutions only for identical effective Claude requests."""

import hashlib
import json

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis

from gopstop_agent.exa import ResearchSource
from gopstop_agent.resolver import ClaudePlaceResolver, SourceResolution


CACHE_TTL_SECONDS = 86400
resolution_adapter = TypeAdapter(SourceResolution | None)


class CachedPlaceResolver:
    def __init__(self, resolver: ClaudePlaceResolver, cache: Redis) -> None:
        self._resolver, self._cache = resolver, cache

    async def resolve(self, description: str, sources: list[ResearchSource]) -> SourceResolution | None:
        if not sources:
            return None
        # Covers model, prompt/schema and ordered evidence, without credentials or session IDs.
        request = self._resolver.request_body(description, sources)
        digest = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        key = f"gopstop:place-resolution:v1:{digest}"
        cached = await self._cache.get(key)
        if cached is not None:
            try:
                place = resolution_adapter.validate_json(cached)
                if place is None or place.sourceIndex < min(len(sources), 3):
                    return place
            except ValidationError:
                pass
        # A cache read outage stops before spending credits; failed writes propagate too.
        place = await self._resolver.resolve(description, sources)
        await self._cache.set(key, resolution_adapter.dump_json(place), ex=CACHE_TTL_SECONDS)
        return place
