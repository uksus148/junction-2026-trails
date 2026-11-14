"""Valkey-backed chat history storage."""

import json
from typing import Protocol

from redis.asyncio import Redis


class SessionStore(Protocol):
    async def record_exchange(self, session_id: str, user_message: str, reply: str) -> None: ...


class ValkeySessionStore:
    def __init__(self, client: Redis, ttl_seconds: int, max_messages: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._max_messages = max_messages

    @staticmethod
    def _key(session_id: str) -> str:
        return f"gopstop:chat-session:{session_id}"

    async def record_exchange(self, session_id: str, user_message: str, reply: str) -> None:
        key = self._key(session_id)
        messages = [
            json.dumps({"role": "user", "content": user_message}, ensure_ascii=False),
            json.dumps({"role": "assistant", "content": reply}, ensure_ascii=False),
        ]
        # A transaction keeps each exchange together and refreshes its session TTL.
        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.rpush(key, *messages)
            pipeline.ltrim(key, -self._max_messages, -1)
            pipeline.expire(key, self._ttl_seconds)
            await pipeline.execute()
