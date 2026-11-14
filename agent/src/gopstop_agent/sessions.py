"""Valkey-backed chat history storage."""

import json
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from gopstop_agent.intent import Message


class SessionStore(Protocol):
    async def history(self, session_id: str) -> list[Message]: ...

    async def record_exchange(self, session_id: str, user_message: str, reply: str) -> None: ...


class ValkeySessionStore:
    def __init__(self, client: Redis, ttl_seconds: int, max_messages: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._max_messages = max_messages

    @staticmethod
    def _key(session_id: str) -> str:
        return f"gopstop:chat-session:{session_id}"

    async def history(self, session_id: str) -> list[Message]:
        # Six complete exchanges keep token use bounded, independently of retention.
        items = await self._client.lrange(self._key(session_id), -12, -1)
        try:
            messages = [json.loads(item) for item in items]
        except (ValueError, TypeError) as exc:
            raise RedisError("Chat history is invalid.") from exc
        if any(not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
               or not isinstance(item.get("content"), str) or not item["content"].strip()
               or len(item["content"]) > 4000 for item in messages):
            raise RedisError("Chat history is invalid.")
        return [{"role": item["role"], "content": item["content"]} for item in messages]

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
