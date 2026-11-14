"""Sourced Exa text research with a 24-hour Valkey response cache."""

import hashlib
import json

import httpx
from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, ValidationError
from redis.asyncio import Redis

from gopstop_agent.intent import ProviderError, ProviderTimeout


CACHE_TTL_SECONDS = 86400
MAX_SOURCE_TEXT = 10000


class ResearchSource(BaseModel):
    """Internal evidence, not a persisted API Place or a licensed Photo."""

    title: str = Field(min_length=1, max_length=2000)
    sourceUrl: HttpUrl
    text: str = Field(default="", max_length=MAX_SOURCE_TEXT)
    # Retrieval provenance only: excluded from ordinary cache/prompt serialization.
    # Old cached/capped text cannot become complete through its length or an LLM claim.
    textComplete: bool = Field(default=False, exclude=True)


sources_adapter = TypeAdapter(list[ResearchSource])


class ExaSearch:
    def __init__(self, client: httpx.AsyncClient, redis: Redis, api_key: str,
                 timeout_seconds: float = 20, *, cache_namespace: str = "gopstop:exa-text:v1") -> None:
        self._client, self._redis, self._api_key = client, redis, api_key
        self._cache_namespace = cache_namespace
        self._timeout = httpx.Timeout(timeout_seconds)

    async def search(self, query: str, *, use_cache: bool = True,
                     include_domains: tuple[str, ...] = (), full_text: bool = False) -> list[ResearchSource]:
        query = query.strip()
        if not query:
            raise ValueError("Search query must not be blank.")
        if full_text and use_cache:
            raise ValueError("Uncapped notice text must remain request-scoped.")
        request_body = {"query": query, "type": "auto", "numResults": 3,
                        "contents": {"text": {"maxCharacters": 2000}}}
        if full_text:
            request_body["contents"] = {"text": True}  # Full body, no maxCharacters/excerpt cap.
        if include_domains:
            request_body["includeDomains"] = list(include_domains)
        digest = hashlib.sha256(json.dumps(request_body, sort_keys=True).encode()).hexdigest()
        key = f"{self._cache_namespace}:{digest}"
        # Fail before spending credits when the cache is unavailable.
        cached = await self._redis.get(key) if use_cache else None
        if cached is not None:
            try:
                return sources_adapter.validate_json(cached)
            except ValidationError:
                pass
        try:
            response = await self._client.post(
                "https://api.exa.ai/search", headers={"x-api-key": self._api_key},
                json=request_body, timeout=self._timeout, follow_redirects=False,
            )
            response.raise_for_status()
            data = response.json()
            results = data["results"]
            if not isinstance(results, list):
                raise ValueError("Expected search results.")
            sources = []
            for item in results:
                try:
                    text = item.get("text") or ""
                    complete = full_text and isinstance(text, str) and bool(text.strip())
                    statuses = data.get("statuses")
                    if statuses is not None:
                        matching = ([s for s in statuses if isinstance(s, dict) and s.get("id") == item["url"]]
                                    if isinstance(statuses, list) else [])
                        complete = complete and len(matching) == 1 and matching[0].get("status") == "success"
                    if full_text and isinstance(text, str) and len(text) > MAX_SOURCE_TEXT:
                        # Retain an incomplete marker instead of dropping a possible
                        # qualifying/revoking notice or slicing it before assessment.
                        text, complete = "", False
                    source = ResearchSource(
                        title=item.get("title") or item["url"], sourceUrl=item["url"],
                        text=text, textComplete=complete,
                    )
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                sources.append(source)
                if len(sources) == 3:
                    break
            if results and not sources:
                raise ProviderError("Place research returned no usable sources.")
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("Place research is temporarily unavailable.") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("Place research is temporarily unavailable.") from exc
        if use_cache:
            await self._redis.set(key, sources_adapter.dump_json(sources), ex=CACHE_TTL_SECONDS)
        return sources
