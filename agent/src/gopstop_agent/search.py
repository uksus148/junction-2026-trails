"""Live Exa research and rate-limited OSM geocoding with shared Valkey caches."""

import asyncio
import hashlib
from typing import Literal

import httpx
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError
from redis.asyncio import Redis

from gopstop_agent.intent import ProviderError


def cache_key(provider: str, query: str) -> str:
    digest = hashlib.sha256(query.strip().encode()).hexdigest()
    return f"gopstop:{provider}:v1:{digest}"


class Source(BaseModel):
    title: str = Field(min_length=1, max_length=2000)
    url: HttpUrl
    text: str = Field(default="", max_length=10000)


sources_adapter = TypeAdapter(list[Source])


class ExaSearch:
    def __init__(self, client: httpx.AsyncClient, redis: Redis, api_key: str) -> None:
        self._client, self._redis, self._api_key = client, redis, api_key

    async def search(self, query: str) -> list[Source]:
        key = cache_key("exa", query)
        cached = await self._redis.get(key)
        if cached is not None:
            try:
                return sources_adapter.validate_json(cached)
            except ValidationError:
                pass
        try:
            response = await self._client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": self._api_key},
                json={"query": query, "type": "auto", "numResults": 3,
                      "contents": {"text": {"maxCharacters": 2000}}},
            )
            response.raise_for_status()
            results = sources_adapter.validate_python(response.json()["results"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Place search is temporarily unavailable.") from exc
        await self._redis.set(key, sources_adapter.dump_json(results), ex=86400)
        return results


class GeocodedPlace(BaseModel):
    osm_type: Literal["node", "way", "relation"]
    osm_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    @property
    def id(self) -> str:
        return f"osm:{self.osm_type}:{self.osm_id}"


class NominatimGeocoder:
    def __init__(self, client: httpx.AsyncClient, redis: Redis, user_agent: str,
                 base_url: str = "https://nominatim.openstreetmap.org") -> None:
        self._client, self._redis = client, redis
        self._user_agent, self._base_url = user_agent, base_url.rstrip("/")

    async def geocode(self, query: str) -> GeocodedPlace | None:
        key = cache_key("nominatim", self._base_url + "|" + query)
        cached = await self._redis.get(key)
        if cached is not None:
            try:
                return None if cached == "null" else GeocodedPlace.model_validate_json(cached)
            except ValidationError:
                pass
        # One shared gate across workers: public Nominatim permits at most 1 req/s.
        while not await self._redis.set("gopstop:nominatim:rate-limit", "1", nx=True, ex=1):
            await asyncio.sleep(1)
        try:
            response = await self._client.get(
                self._base_url + "/search",
                headers={"User-Agent": self._user_agent},
                params={"q": query, "format": "jsonv2", "limit": 2},
            )
            response.raise_for_status()
            results = response.json()
            if not isinstance(results, list):
                raise ValueError("Expected a list of geocoding candidates.")
            # Ambiguous results require a more specific description, not a guess.
            place = None
            if len(results) == 1:
                item = results[0]
                place = GeocodedPlace(
                    osm_type=item["osm_type"], osm_id=item["osm_id"],
                    name=item["display_name"], lat=item["lat"], lon=item["lon"],
                )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Place geocoding is temporarily unavailable.") from exc
        await self._redis.set(key, place.model_dump_json() if place else "null", ex=86400)
        return place
