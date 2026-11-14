import json

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import RedisError, TimeoutError

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


@pytest.mark.parametrize("failure", [RedisError("connection failed"), TimeoutError("timed out")])
def test_chat_reports_storage_failure_as_service_unavailable(fake_redis, failure):
    app = create_app(Settings(), redis_client=fake_redis)
    with TestClient(app) as client:
        async def fail_exchange(*args, **kwargs):
            raise failure

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


async def test_history_is_bounded_and_isolated_by_session(fake_redis):
    store = ValkeySessionStore(fake_redis, ttl_seconds=600, max_messages=200)
    for index in range(8):
        await store.record_exchange("first", str(index), "reply")
    await store.record_exchange("second", "private request", "private reply")
    history = await store.history("first")
    assert len(history) == 12
    assert history[0] == {"role": "user", "content": "2"}
    assert all("private" not in item["content"] for item in history)
    assert await store.history("unknown") == []


def test_browser_preflight_and_post_have_cors_headers(client):
    origin = "http://localhost:5173"
    preflight = client.options("/api/chat", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-methods"] == "POST"
    response = client.post("/api/chat", headers={"Origin": origin},
                           json={"sessionId": "browser", "message": "Find Skok"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_uses_configured_origins(fake_redis):
    app = create_app(Settings(cors_origins=["https://trails.example.org"]), fake_redis)
    with TestClient(app) as client:
        for origin, expected in [("https://trails.example.org", 200),
                                 ("https://other.example.org", 400)]:
            response = client.options("/api/chat", headers={
                "Origin": origin, "Access-Control-Request-Method": "POST",
            })
            assert response.status_code == expected
            assert response.headers.get("access-control-allow-origin") == (
                origin if expected == 200 else None
            )


def test_production_client_has_bounded_timeouts(monkeypatch):
    import gopstop_agent.main as main

    seen = {}

    def capture_client(url, **kwargs):
        seen.update(kwargs)
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    monkeypatch.setattr(main, "from_url", capture_client)
    with TestClient(create_app(Settings(valkey_connect_timeout_seconds=0.2,
                                        valkey_socket_timeout_seconds=0.3))):
        assert seen["socket_connect_timeout"] == 0.2
        assert seen["socket_timeout"] == 0.3
        assert seen["retry"].get_retries() == 0
