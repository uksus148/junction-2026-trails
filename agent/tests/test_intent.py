import json

import httpx
import pytest

from gopstop_agent.intent import ClaudeIntentExtractor, ProviderError


def tool_response(intent):
    return {"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "name": "extract_route_intent", "input": intent,
    }]}


async def test_extracts_tatras_intent_and_sends_history():
    intent = {"start": "Štrbské Pleso", "end": "Rysy",
              "mustSee": ["Skok waterfall"], "preferences": ["wild scenery"]}
    captured = []

    def handle(request):
        captured.append(json.loads(request.content))
        assert request.headers["x-api-key"] == "fixture-key"
        assert request.url == "https://api.anthropic.com/v1/messages"
        return httpx.Response(200, json=tool_response(intent))

    history = [{"role": "user", "content": "Hike from Štrbské Pleso to Rysy"},
               {"role": "assistant", "content": "Any places to visit?"}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        parsed = await ClaudeIntentExtractor(client, "fixture-key", "fixture-model").extract(
            "Via Skok waterfall, I love wild scenery", history,
        )
    assert parsed.model_dump() == intent
    assert captured[0]["messages"][:-1] == history
    assert captured[0]["model"] == "fixture-model"
    assert captured[0]["tool_choice"]["name"] == "extract_route_intent"


async def test_unknown_endpoints_remain_unknown():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=tool_response({"mustSee": ["a waterfall near Tromsø"]})),
    )) as client:
        result = await ClaudeIntentExtractor(client, "fixture", "model").extract("Find a waterfall", [])
    assert result.start is None and result.end is None
    assert result.mustSee == ["a waterfall near Tromsø"]


@pytest.mark.parametrize("body", [
    {}, {"stop_reason": "max_tokens", "content": []},
    {"stop_reason": "tool_use", "content": []},
    tool_response({"start": {"lat": 49, "lon": 20}}),
    tool_response({"end": " "}), tool_response({"mustSee": ["x"] * 6}),
    tool_response({"preferences": "scenery"}), tool_response({"invented": True}),
])
async def test_rejects_incomplete_or_invalid_provider_output(body):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=body),
    )) as client:
        with pytest.raises(ProviderError):
            await ClaudeIntentExtractor(client, "fixture", "model").extract("test", [])


@pytest.mark.parametrize("code", [401, 429, 503])
async def test_upstream_errors_do_not_expose_provider_details(code):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(code, json={"error": "sensitive upstream details"}),
    )) as client:
        with pytest.raises(ProviderError, match="temporarily unavailable") as error:
            await ClaudeIntentExtractor(client, "fixture", "model").extract("test", [])
    assert "sensitive" not in str(error.value)
