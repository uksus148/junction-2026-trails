import asyncio
from unittest.mock import AsyncMock

import pytest

from gopstop_agent.discovery import PlaceDiscovery
from gopstop_agent.exa import ResearchSource
from gopstop_agent.geocoding import GeocodedPlace
from gopstop_agent.intent import ProviderError, RouteIntent
from gopstop_agent.resolver import SourceResolution


@pytest.mark.parametrize("failure", [False, True])
async def test_research_is_bounded_ordered_and_joined_before_return_or_failure(failure):
    intent, search, resolver, geocoder = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    intent.extract.return_value = RouteIntent(start="A", end="G", mustSee=list("BCDEF"))
    active, maximum, arrivals, cancelled = 0, 0, 0, 0
    started = asyncio.Event()

    async def research(query):
        nonlocal active, maximum, arrivals, cancelled
        name = query.removeprefix("Find hiking place: ").split(". Route context:")[0]
        active += 1; arrivals += 1; maximum = max(maximum, active)
        if arrivals == 3: started.set()
        try:
            await asyncio.wait_for(started.wait(), 1)
            if failure and name == "A": raise ProviderError("fixture failure")
            if failure: await asyncio.sleep(10)
            await asyncio.sleep(0)
            return [ResearchSource(title=name, sourceUrl="https://source.example/", text="Evidence")]
        except asyncio.CancelledError:
            cancelled += 1
            raise
        finally:
            active -= 1

    async def resolve(query, sources):
        name = sources[0].title
        return SourceResolution(name=name, geocodeQuery=name, sourceIndex=0)

    search.search.side_effect = research
    resolver.resolve.side_effect = resolve
    geocoder.geocode.return_value = GeocodedPlace(osm_type="node", osm_id=1, display_name="Fixture", lat=49, lon=20)
    discovery = PlaceDiscovery(intent, search, resolver, geocoder)
    if failure:
        with pytest.raises(ProviderError, match="fixture failure"):
            await discovery.discover("Hike", [])
        assert cancelled >= 2
    else:
        result = await discovery.discover("Hike", [])
        assert [finding.place.name for finding in [result.start, *result.stops, result.end]] == list("ABCDEFG")
    assert maximum == 3 and active == 0
    count = search.search.await_count
    await asyncio.sleep(0)
    assert search.search.await_count == count  # No unfinished provider work after the call ends.
