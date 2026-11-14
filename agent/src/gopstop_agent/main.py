"""FastAPI application and baseline chat endpoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from redis.asyncio import Redis, from_url
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from gopstop_agent.config import Settings
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


class ChatResponse(BaseModel):
    reply: str
    places: list[dict[str, object]]
    routeId: str | None = None


def create_app(
    settings: Settings | None = None,
    redis_client: Redis | None = None,
) -> FastAPI:
    configured = settings or Settings()
    owns_client = redis_client is None

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
        app.state.session_store = ValkeySessionStore(
            client,
            ttl_seconds=configured.session_ttl_seconds,
            max_messages=configured.session_max_messages,
        )
        try:
            yield
        finally:
            if owns_client:
                await client.aclose()

    app = FastAPI(title="trego. Agent", version="0.1.0", lifespan=lifespan)
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
        session_store: SessionStore = Depends(get_session_store),
    ) -> ChatResponse:
        # Keep the MVP honest until intent extraction and place search are integrated.
        reply = "Thanks, I’ve saved your request. Place discovery and route planning are not configured yet."
        try:
            await session_store.record_exchange(payload.sessionId, payload.message, reply)
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat session storage is temporarily unavailable.",
            ) from exc
        return ChatResponse(reply=reply, places=[])

    return app


app = create_app()
