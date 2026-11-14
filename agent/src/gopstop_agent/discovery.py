"""Find sourced, uniquely geocoded places without inventing a hiking route."""

from gopstop_agent.intent import ClaudeIntentExtractor, Message
from gopstop_agent.places import ChatResponse, Place
from gopstop_agent.resolver import ClaudePlaceResolver
from gopstop_agent.search import ExaSearch, NominatimGeocoder


class DiscoveryChat:
    def __init__(self, intent: ClaudeIntentExtractor, search: ExaSearch,
                 resolver: ClaudePlaceResolver, geocoder: NominatimGeocoder) -> None:
        self._intent, self._search = intent, search
        self._resolver, self._geocoder = resolver, geocoder

    async def respond(self, message: str, history: list[Message]) -> ChatResponse:
        intent = await self._intent.extract(message, history)
        targets = list(dict.fromkeys(
            name for name in [intent.start, *intent.mustSee, intent.end] if name
        ))
        if not targets:
            return ChatResponse(reply="Where would you like to hike? Name a start, finish, or place to visit.",
                                places=[])
        places: dict[str, Place] = {}
        unresolved = []
        for target in targets:
            query = f"{target}. Hiking trip from {intent.start or 'unspecified'} to {intent.end or 'unspecified'}."
            sources = await self._search.search(query)
            resolution = await self._resolver.resolve(query, sources)
            location = await self._geocoder.geocode(resolution.geocodeQuery) if resolution else None
            if not location:
                unresolved.append(target)
                continue
            place = Place(
                id=location.id, name=resolution.name, lat=location.lat, lon=location.lon,
                tags=resolution.tags, source=str(sources[resolution.sourceIndex].url),
            )
            places.setdefault(place.id, place)
        lines = [f"Found {place.name}: {place.source}" for place in places.values()]
        if unresolved:
            lines.append("Please give a more specific location for: " + ", ".join(unresolved) + ".")
        if not intent.start or not intent.end:
            lines.append("Please name both your starting point and destination to plan a hike.")
        lines.append("A hiking route has not been built yet.")
        if places:
            lines.append("Coordinates © OpenStreetMap contributors: https://www.openstreetmap.org/copyright")
        return ChatResponse(reply="\n".join(lines), places=list(places.values()))
