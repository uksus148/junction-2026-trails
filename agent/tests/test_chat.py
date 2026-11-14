import json

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from gopstop_agent.config import Settings
from gopstop_agent.main import create_app
from gopstop_agent.sessions import ValkeySessionStore


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(fake_redis):
    app = create_app(Settings(), redis_client=fake_redis)
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_chat_returns_contract_response_and_persists_exchange(client, fake_redis):
    response = client.post(
        "/api/chat",
        json={"sessionId": "tatras-1", "message": "Find a waterfall near Štrbské Pleso"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"reply", "places"}
    assert body["places"] == []
    stored = await fake_redis.lrange("gopstop:chat-session:tatras-1", 0, -1)
    assert [json.loads(message) for message in stored] == [
        {"role": "user", "content": "Find a waterfall near Štrbské Pleso"},
        {"role": "assistant", "content": body["reply"]},
    ]


@pytest.mark.asyncio
async def test_chat_reuses_session_and_keeps_newest_messages(client, fake_redis):
    client.post("/api/chat", json={"sessionId": "same", "message": "First"})
    client.post("/api/chat", json={"sessionId": "same", "message": "Second"})

    stored = await fake_redis.lrange("gopstop:chat-session:same", 0, -1)
    messages = [json.loads(item) for item in stored]
    assert len(messages) == 4
    assert messages[0] == {"role": "user", "content": "First"}
    assert messages[2] == {"role": "user", "content": "Second"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"sessionId": "s", "message": ""},
        {"sessionId": "s", "message": "   "},
        {"sessionId": "", "message": "hello"},
        {"sessionId": "s", "message": "hello", "unexpected": True},
        {"sessionId": "s", "message": "x" * 4001},
    ],
)
def test_chat_rejects_invalid_input(client, payload):
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 422


def test_chat_reports_storage_failure_as_service_unavailable(fake_redis):
    app = create_app(Settings(), redis_client=fake_redis)
    with TestClient(app) as client:
        async def fail_exchange(*args, **kwargs):
            raise RedisError("connection failed")

        app.state.session_store.record_exchange = fail_exchange
        response = client.post("/api/chat", json={"sessionId": "s", "message": "hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Chat session storage is temporarily unavailable."


@pytest.mark.asyncio
async def test_session_store_refreshes_expiry_and_caps_history(fake_redis):
    store = ValkeySessionStore(fake_redis, ttl_seconds=600, max_messages=2)

    await store.record_exchange("bounded", "one", "reply one")
    await store.record_exchange("bounded", "two", "reply two")

    messages = [json.loads(item) for item in await fake_redis.lrange("gopstop:chat-session:bounded", 0, -1)]
    assert len(messages) == 2
    assert messages == [
        {"role": "user", "content": "two"},
        {"role": "assistant", "content": "reply two"},
    ]
    assert 0 < await fake_redis.ttl("gopstop:chat-session:bounded") <= 600
