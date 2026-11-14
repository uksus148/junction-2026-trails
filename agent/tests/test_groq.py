import asyncio
import json
from copy import deepcopy

import fakeredis.aioredis
import httpx
import pytest

from gopstop_agent.config import Settings
from gopstop_agent.llm import ProviderError, ProviderTimeout, ToolModel, inline_tool_schema
from gopstop_agent.resolution_cache import CachedPlaceResolver
from gopstop_agent.resolver import ClaudePlaceResolver
from test_resolution_cache import PLACE, SOURCES


def completion(name="resolve_place", value=None, finish="tool_calls"):
    return {"choices": [{"finish_reason": finish, "message": {"tool_calls": [{
        "type": "function", "function": {"name": name, "arguments": json.dumps(value or {"place": PLACE})},
    }]}}]}


def request_body():
    return ClaudePlaceResolver(None, "unused", "openai/gpt-oss-20b").request_body("Skok", SOURCES)


@pytest.mark.parametrize("finish", ["tool_calls", "stop"])
async def test_groq_sends_forced_function_and_normalizes_only_its_validated_input(finish):
    original = request_body()
    snapshot = deepcopy(original)

    def handle(request):
        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer fixture-secret"
        assert "x-api-key" not in request.headers
        assert request.extensions["timeout"]["read"] == .5
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-20b" and body["reasoning_effort"] == "low"
        assert body["max_completion_tokens"] == 2048 and not body["parallel_tool_calls"]
        assert body["messages"][0]["role"] == "system"
        parameters = body["tools"][0]["function"]["parameters"]
        expected = deepcopy(snapshot["tools"][0]["input_schema"])
        definition = expected.pop("$defs")["SourceResolution"]
        expected["properties"]["place"]["anyOf"] = [definition, {"type": "null"}]
        assert parameters == expected  # Retain required fields, bounds and extra-field rejection.
        assert '"$ref"' not in json.dumps(parameters) and '"$defs"' not in json.dumps(parameters)
        assert body["tool_choice"] == {"type": "function", "function": {"name": "resolve_place"}}
        return httpx.Response(200, json=completion(finish=finish))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await ToolModel(client, "fixture-secret", "groq", .5).call(original) == {"place": PLACE}
    assert original == snapshot


async def test_anthropic_keeps_the_original_pydantic_schema():
    body = request_body()

    def handle(request):
        assert json.loads(request.content) == body
        assert "$defs" in body["tools"][0]["input_schema"]
        return httpx.Response(200, json={"stop_reason": "tool_use", "content": [{
            "type": "tool_use", "name": "resolve_place", "input": {"place": PLACE},
        }]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await ToolModel(client, "fixture").call(body) == {"place": PLACE}


def test_inline_schema_expands_shared_nested_refs_and_preserves_sibling_constraints():
    schema = {
        "$defs": {"Name": {"type": "string", "minLength": 1},
                  "Names": {"type": "array", "items": {"$ref": "#/$defs/Name"}}},
        "type": "object", "properties": {
            "names": {"$ref": "#/$defs/Names"},
            "name": {"$ref": "#/$defs/Name", "minLength": 3},
        },
    }
    assert inline_tool_schema(schema) == {
        "type": "object", "properties": {
            "names": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "name": {"allOf": [{"type": "string", "minLength": 1}, {"minLength": 3}]},
        },
    }


@pytest.mark.parametrize("schema", [
    {"$ref": "https://untrusted.example/schema"}, {"$ref": "#/$defs/Missing"},
    {"$defs": {"Loop": {"$ref": "#/$defs/Loop"}}, "$ref": "#/$defs/Loop"},
    {"$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"$ref": "#/$defs/A"}}, "$ref": "#/$defs/A"},
])
async def test_unsupported_schema_fails_safely_before_groq_request(schema):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=completion())

    body = request_body()
    body["tools"][0]["input_schema"] = schema
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError, match="^Model request is temporarily unavailable.$"):
            await ToolModel(client, "fixture", "groq").call(body)
    assert calls == []


@pytest.mark.parametrize("bad", [{}, {"choices": []}, completion(finish="length"), completion(name="invented", finish="stop"),
                                 completion(value=[1]), {"choices": completion()["choices"] * 2},
                                 {"choices": [{"finish_reason": "stop", "message": {"tool_calls": []}}]}])
async def test_bad_groq_response_is_a_safe_failure_without_retry(bad):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=bad)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError):
            await ToolModel(client, "fixture", "groq").call(request_body())
    assert len(calls) == 1


@pytest.mark.parametrize("failure", [400, 401, 429, 307, "timeout", "invalid_json", "two_tools"])
async def test_groq_failures_do_not_leak_retry_redirect_or_fall_back(failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private upstream body")
        if failure in ("invalid_json", "two_tools"):
            body = completion()
            if failure == "invalid_json":
                body["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "not JSON private"
            else:
                body["choices"][0]["message"]["tool_calls"] *= 2
            return httpx.Response(200, json=body)
        return httpx.Response(failure, text="private upstream body", headers={"Location": "https://unsafe.example"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), follow_redirects=True) as client:
        with pytest.raises(ProviderError) as error:
            await ToolModel(client, "fixture", "groq").call(request_body())
    assert isinstance(error.value, ProviderTimeout) == (failure == "timeout")
    assert len(calls) == 1 and "private" not in str(error.value)


@pytest.mark.parametrize("cancel", [False, True])
async def test_groq_header_wait_is_serialized_and_cancellable(monkeypatch, cancel):
    calls, waits = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=completion(), headers={
            "x-ratelimit-remaining-tokens": "0", "x-ratelimit-reset-tokens": "1m20s",
        })

    async def fake_sleep(seconds):
        waits.append(seconds)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        model = ToolModel(client, "fixture", "groq")
        await model.call(request_body())
        if cancel:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(.01):
                    await model.call(request_body())
            assert len(calls) == 1
        else:
            monkeypatch.setattr("gopstop_agent.llm.asyncio.sleep", fake_sleep)
            await model.call(request_body())
            assert len(calls) == 2 and waits[0] == pytest.approx(80, abs=1)


async def test_resolution_cache_separates_providers_even_with_identical_model_names():
    calls = []

    def handle(request):
        calls.append(request)
        body = completion() if request.url.host == "api.groq.com" else {
            "stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "resolve_place", "input": {"place": PLACE}}],
        }
        return httpx.Response(200, json=body)

    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as cache:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            for provider in ("groq", "anthropic", "groq", "anthropic"):
                resolver = ClaudePlaceResolver(client, "fixture", "same-model",
                                               tool_model=ToolModel(client, "fixture", provider))
                assert (await CachedPlaceResolver(resolver, cache).resolve("Skok", SOURCES)).model_dump() == PLACE
        assert len(calls) == 2


def test_groq_environment_selects_only_its_key_and_masks_secrets(monkeypatch):
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "private-groq-secret")
    monkeypatch.setenv("EXA_API_KEY", "private-exa-secret")
    settings = Settings(_env_file=None, anthropic_api_key="")
    settings.require_chat_configuration()
    assert settings.llm_model == "openai/gpt-oss-20b"
    assert "private-groq-secret" not in repr(settings) and "private-exa-secret" not in repr(settings)
