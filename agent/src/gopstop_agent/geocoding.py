"""Cached Nominatim lookup with a distributed request gate and OSM attribution."""

import asyncio
import hashlib
import math
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from redis.asyncio import Redis

from gopstop_agent.intent import ProviderError, ProviderTimeout


OSM_ATTRIBUTION = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"
COOLDOWN = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], 1000)
end
return 0
"""


class GeocodedPlace(BaseModel):
    osm_type: Literal["node", "way", "relation"]
    osm_id: int = Field(gt=0)
    display_name: str = Field(min_length=1, max_length=2000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_type}/{self.osm_id}"


cached_location = TypeAdapter(GeocodedPlace | None)
locations_adapter = TypeAdapter(list[GeocodedPlace])


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

    async def geocode(self, query: str) -> GeocodedPlace | None:
        query = query.strip()
        if not query:
            raise ValueError("Geocoding query must not be blank.")
        digest = hashlib.sha256((self._base_url + "|" + query).encode()).hexdigest()
        key = f"gopstop:nominatim:result:v1:{digest}"
        cached = await self._redis.get(key)
        if cached is not None:
            try:
                return cached_location.validate_json(cached)
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
                        self._base_url + "/search", timeout=self._timeout,
                        headers={"User-Agent": self._user_agent},
                        params={"q": query, "format": "jsonv2", "limit": 2},
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
        place = results[0] if len(results) == 1 else None
        await self._redis.set(key, cached_location.dump_json(place), ex=86400)
        return place
