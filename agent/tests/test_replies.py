import json

import httpx
import pytest

from gopstop_agent.intent import ProviderError, ProviderTimeout
from gopstop_agent.replies import ClaudeReplyWriter
from test_discovery import tool


@pytest.mark.parametrize("message,reply", [("Где маршрут?", "Маршрут готов."),
                                          ("Missä reitti on?", "Reitti on valmis.")])
async def test_reply_uses_authoritative_outcome_and_language_instruction(message, reply):
    calls = []

    def handle(request):
        calls.append(request)
        body = json.loads(request.content)
        assert "language of the latest user message" in body["system"]
        assert "untrusted data" in body["system"]
        assert request.extensions["timeout"]["read"] == 3
        content = json.loads(body["messages"][0]["content"])
        assert content == {"message": message, "history": [], "outcome": "ready", "facts": {"distanceKm": 7.5}}
        return tool("write_chat_reply", {"reply": reply})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await ClaudeReplyWriter(client, "fixture", "model", 3).write(message, [], "ready", {"distanceKm": 7.5})
    assert result == reply and len(calls) == 1


@pytest.mark.parametrize("payload", [{"reply": " "}, {"reply": "x" * 2001}, {"reply": 1},
                                     {"reply": "Ready", "routeId": "invented"}])
async def test_invalid_reply_is_not_used_as_success(payload):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: tool("write_chat_reply", payload),
    )) as client:
        with pytest.raises(ProviderError):
            await ClaudeReplyWriter(client, "fixture", "model").write("hi", [], "ready", {})


@pytest.mark.parametrize("failure", ["http", "truncated", "timeout"])
async def test_reply_failures_are_safe_and_not_retried(failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider details")
        if failure == "http":
            return httpx.Response(401, text="private provider details")
        return httpx.Response(200, json={"stop_reason": "max_tokens", "content": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError) as error:
            await ClaudeReplyWriter(client, "fixture", "model").write("hi", [], "clarification", {})
    assert len(calls) == 1 and "private" not in str(error.value)
    assert isinstance(error.value, ProviderTimeout) == (failure == "timeout")
