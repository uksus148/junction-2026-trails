"""FastAPI application and baseline chat endpoint."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from redis.asyncio import Redis, from_url
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from gopstop_agent.config import Settings
from gopstop_agent.discovery import DiscoveryChat
from gopstop_agent.intent import ClaudeIntentExtractor, ProviderError
from gopstop_agent.places import ChatResponse
from gopstop_agent.resolver import ClaudePlaceResolver
from gopstop_agent.search import ExaSearch, NominatimGeocoder
from gopstop_agent.sessions import SessionStore, ValkeySessionStore


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessionId: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("sessionId", "message")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def create_app(
    settings: Settings | None = None,
    redis_client: Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    configured = settings or Settings()
    owns_client = redis_client is None
    if configured.enable_discovery and not (
        configured.anthropic_api_key.get_secret_value() and configured.exa_api_key.get_secret_value()
    ):
        raise ValueError("Discovery requires ANTHROPIC_API_KEY and EXA_API_KEY.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = (
            redis_client
            if redis_client is not None
            else from_url(
                str(configured.valkey_url),
                decode_responses=True,
                socket_connect_timeout=configured.valkey_connect_timeout_seconds,
                socket_timeout=configured.valkey_socket_timeout_seconds,
                retry=Retry(NoBackoff(), 0),
            )
        )
        web = http_client or httpx.AsyncClient(timeout=configured.provider_timeout_seconds)
        app.state.session_store = ValkeySessionStore(
            client,
            ttl_seconds=configured.session_ttl_seconds,
            max_messages=configured.session_max_messages,
        )
        app.state.discovery = None
        if configured.enable_discovery:
            key = configured.anthropic_api_key.get_secret_value()
            app.state.discovery = DiscoveryChat(
                ClaudeIntentExtractor(web, key, configured.anthropic_model),
                ExaSearch(web, client, configured.exa_api_key.get_secret_value()),
                ClaudePlaceResolver(web, key, configured.anthropic_model),
                NominatimGeocoder(web, client, configured.nominatim_user_agent,
                                  configured.nominatim_base_url),
            )
        try:
            yield
        finally:
            if http_client is None:
                await web.aclose()
            if owns_client:
                await client.aclose()

    app = FastAPI(title="GOPSTOP.PROTOCOL Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configured.cors_origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    def get_session_store(request: Request) -> SessionStore:
        return request.app.state.session_store

    @app.post("/api/chat", response_model=ChatResponse, response_model_exclude_none=True)
    async def chat(
        payload: ChatRequest,
        request: Request,
        session_store: SessionStore = Depends(get_session_store),
    ) -> ChatResponse:
        try:
            async with asyncio.timeout(configured.chat_timeout_seconds):
                discovery = request.app.state.discovery
                if discovery is None:
                    response = ChatResponse(
                        reply="Thanks, I’ve saved your request. Place discovery and route planning are not configured yet.",
                        places=[],
                    )
                else:
                    response = await discovery.respond(
                        payload.message, await session_store.history(payload.sessionId),
                    )
                await session_store.record_exchange(payload.sessionId, payload.message, response.reply)
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat session storage is temporarily unavailable.",
            ) from exc
        except (ProviderError, TimeoutError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Place discovery is temporarily unavailable. Please try again later.",
            ) from exc
        return response

    return app


app = create_app()
