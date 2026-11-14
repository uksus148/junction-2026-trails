import json

import httpx
import pytest

from gopstop_agent.exa import ResearchSource
from gopstop_agent.intent import ProviderError
from gopstop_agent.resolver import ClaudePlaceResolver


def tool(place):
    return {"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "name": "resolve_place", "input": {"place": place},
    }]}


async def test_description_is_resolved_from_evidence_with_a_known_source():
    expected = {"name": "Skok waterfall", "geocodeQuery": "Skok, High Tatras, Slovakia",
                "sourceIndex": 0, "tags": ["waterfall"]}

    def handle(request):
        body = json.loads(request.content)
        evidence = json.loads(body["messages"][0]["content"])
        assert evidence["sources"][0]["sourceUrl"] == "https://example.org/skok"
        assert evidence["description"] == "waterfall from TikTok near Štrbské Pleso"
        assert request.extensions["timeout"]["read"] == 0.5
        return httpx.Response(200, json=tool(expected))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await ClaudePlaceResolver(client, "fixture", "model", 0.5).resolve(
            "waterfall from TikTok near Štrbské Pleso",
            [ResearchSource(title="Skok", sourceUrl="https://example.org/skok")],
        )
    assert result.model_dump() == expected


@pytest.mark.parametrize("place", [None, {"name": " ", "geocodeQuery": "", "sourceIndex": 0}])
async def test_unresolved_or_blank_places_are_not_guessed(place):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=tool(place)),
    )) as client:
        resolver = ClaudePlaceResolver(client, "fixture", "model")
        assert await resolver.resolve("unknown", [ResearchSource(title="source", sourceUrl="https://example.org/")]) is None


@pytest.mark.parametrize("place", [
    {"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": 1},
    {"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": -1},
    {"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": 0, "sourceUrl": "https://invented.org/"},
])
async def test_invalid_or_invented_source_references_are_rejected(place):
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=tool(place)),
    )) as client:
        with pytest.raises(ProviderError):
            await ClaudePlaceResolver(client, "fixture", "model").resolve(
                "Skok", [ResearchSource(title="Skok", sourceUrl="https://example.org/")],
            )


async def test_no_evidence_does_not_spend_model_credits():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: pytest.fail("No evidence should require no model call"),
    )) as client:
        assert await ClaudePlaceResolver(client, "fixture", "model").resolve("unknown", []) is None


@pytest.mark.parametrize("failure", [401, httpx.ReadTimeout, "truncated"])
async def test_failed_or_incomplete_resolution_is_not_retried(failure):
    calls = []

    def handle(request):
        calls.append(request)
        if failure == 401:
            return httpx.Response(401, text="private provider details")
        if failure == "truncated":
            return httpx.Response(200, json={"stop_reason": "max_tokens", "content": []})
        raise failure("private provider details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ProviderError) as error:
            await ClaudePlaceResolver(client, "fixture", "model").resolve(
                "Skok", [ResearchSource(title="Skok", sourceUrl="https://example.org/")],
            )
    assert len(calls) == 1 and "private" not in str(error.value)
