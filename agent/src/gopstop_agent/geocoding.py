"""Cached Nominatim lookup with a distributed request gate and OSM attribution."""

import asyncio
import hashlib
import json
import math
from uuid import uuid4

import httpx
from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis

from gopstop_agent.intent import ProviderError, ProviderTimeout
from gopstop_agent.geocoding_candidates import GeocodingCandidate, select_candidate
from gopstop_agent.geocoding_models import GeocodedPlace


OSM_ATTRIBUTION = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"
COOLDOWN = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], 1000)
end
return 0
"""


locations_adapter = TypeAdapter(list[GeocodingCandidate])
SEARCH_OPTIONS = {"format": "jsonv2", "limit": 8, "namedetails": 1}


class NominatimGeocoder:
    def __init__(self, client: httpx.AsyncClient, redis: Redis, user_agent: str,
                 base_url: str = "https://nominatim.openstreetmap.org",
                 timeout_seconds: float = 20) -> None:
        self._client, self._redis, self._user_agent = client, redis, user_agent
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._timeout = httpx.Timeout(timeout_seconds)
        host_hash = hashlib.sha256(self._base_url.encode()).hexdigest()
        self._gate = f"gopstop:nominatim:gate:v1:{host_hash}"

    async def geocode(self, query: str, *, name: str | None = None, tags: list[str] | None = None,
                      anchors: list[GeocodedPlace] | None = None) -> GeocodedPlace | None:
        query = query.strip()
        if not query:
            raise ValueError("Geocoding query must not be blank.")
        try:
            async with asyncio.timeout(self._timeout_seconds):
                candidates = await self._search(query)
                parts = [part.strip() for part in query.split(",")]
                # Preserve the supplied name and country; remove only intermediate
                # region qualifiers after an empty response, never after an error.
                if not candidates and len(parts) >= 3 and all(parts):
                    candidates = await self._search(f"{parts[0]}, {parts[-1]}")
                return select_candidate(candidates, name or parts[0], tags or [], anchors or [])
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise ProviderTimeout("Place geocoding is temporarily unavailable.") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError("Place geocoding is temporarily unavailable.") from exc

    async def _search(self, query: str) -> list[GeocodingCandidate]:
        identity = json.dumps([self._base_url, query, SEARCH_OPTIONS], sort_keys=True)
        digest = hashlib.sha256(identity.encode()).hexdigest()
        # v1 cached a selected place/null for 24h. v2 retains candidates so a
        # different category or geographic context cannot inherit an old decision.
        key = f"gopstop:nominatim:search:v2:{digest}"
        cached = await self._redis.get(key)
        if cached is not None:
            try:
                return locations_adapter.validate_json(cached)
            except ValidationError:
                pass
        try:
            async with asyncio.timeout(self._timeout_seconds):
                token = uuid4().hex
                lease_ms = math.ceil(self._timeout_seconds * 1000) + 2000
                while not await self._redis.set(self._gate, token, nx=True, px=lease_ms):
                    await asyncio.sleep(0.05)
                try:
                    response = await self._client.get(
                        self._base_url + "/search", timeout=self._timeout, follow_redirects=False,
                        headers={"User-Agent": self._user_agent},
                        params={"q": query, **SEARCH_OPTIONS},
                    )
                    response.raise_for_status()
                    results = locations_adapter.validate_python(response.json())
                finally:
                    # Keep one second between completion and the next uncached request.
                    # Compare the token so a timed-out worker cannot release another's gate.
                    await self._redis.eval(COOLDOWN, 1, self._gate, token)
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise ProviderTimeout("Place geocoding is temporarily unavailable.") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError("Place geocoding is temporarily unavailable.") from exc
        await self._redis.set(key, locations_adapter.dump_json(results), ex=86400 if results else 300)
        return results
