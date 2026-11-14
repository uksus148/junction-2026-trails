import httpx
import pytest

from gopstop_agent.intent import ProviderError
from gopstop_agent.resolver import ClaudePlaceResolver
from gopstop_agent.search import Source


@pytest.mark.parametrize("place,valid", [
    (None, True),
    ({"name": "Skok", "geocodeQuery": "Skok, High Tatras, Slovakia", "sourceIndex": 0}, True),
    ({"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": 1}, False),
    ({"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": -1}, False),
    ({"name": "Skok", "geocodeQuery": "Skok", "sourceIndex": 0,
      "sourceUrl": "https://invented.example/"}, False),
])
async def test_place_resolution_uses_only_supplied_sources(place, valid):
    response = {"stop_reason": "tool_use", "content": [{
        "type": "tool_use", "name": "resolve_place", "input": {"place": place},
    }]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=response),
    )) as client:
        resolver = ClaudePlaceResolver(client, "fixture", "fixture-model")
        sources = [Source(title="Skok waterfall", url="https://example.org/skok")]
        if valid:
            result = await resolver.resolve("waterfall from TikTok near Štrbské Pleso", sources)
            assert (result.model_dump() if result else None) == (
                {**place, "tags": []} if place else None
            )
        else:
            with pytest.raises(ProviderError):
                await resolver.resolve("waterfall", sources)
