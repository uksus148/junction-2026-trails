"""Bounded, non-retrying HTTP adapter for the accepted place/route contract."""

from urllib.parse import quote

import httpx
from pydantic import HttpUrl, TypeAdapter, ValidationError

from gopstop_agent.api_models import ApiPlace, ApiProblem, ApiRoute
from gopstop_agent.discovery import DiscoveredPlace


class HandoffError(Exception):
    """Safe dependency error for future HTTP wiring; never includes API bodies."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        self.status_code = status_code
        super().__init__(message)


class NoHikingRoute(Exception):
    """A verified no-route result, distinct from a dependency outage."""


url_adapter = TypeAdapter(HttpUrl)


class TrailsApi:
    def __init__(self, client: httpx.AsyncClient, base_url: str,
                 timeout_seconds: float = 20) -> None:
        self._client = client
        self._base = str(url_adapter.validate_python(base_url)).rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)

    async def _request(self, method: str, path: str, success: tuple[int, ...],
                       *, payload: dict | None = None, allow_no_route: bool = False) -> httpx.Response:
        try:
            response = await self._client.request(
                method, self._base + path, json=payload, timeout=self._timeout,
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            raise HandoffError("Trail API timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise HandoffError("Trail API is temporarily unavailable.") from exc
        if response.status_code in success:
            return response
        if allow_no_route and response.status_code == 422:
            try:
                problem = ApiProblem.model_validate_json(response.content)
            except ValidationError:
                problem = None
            if problem and problem.status == 422 and problem.code == "no_hiking_route":
                raise NoHikingRoute("No walking route connects the requested waypoints.")
        status = response.status_code if response.status_code in (503, 504) else 502
        raise HandoffError("Trail API could not complete the operation.", status)

    async def ingest(self, candidate: DiscoveredPlace) -> ApiPlace:
        source = str(candidate.source.sourceUrl)
        response = await self._request("POST", "/api/places", (200, 201), payload={
            "name": candidate.name, "lat": candidate.location.lat, "lon": candidate.location.lon,
            "tags": candidate.tags,
            "provenance": {"sourceUrl": source, "osmType": candidate.location.osm_type,
                           "osmId": candidate.location.osm_id},
        })
        try:
            place = ApiPlace.model_validate_json(response.content)
            persisted_source = url_adapter.validate_python(place.source)
            # The current manual-only handler ignores provenance; fail closed if it is used.
            # A 200 replay may retain an earlier research URL under first-write-wins.
            if response.status_code == 201 and persisted_source != candidate.source.sourceUrl:
                raise ValueError("New researched place lost its source.")
            return place
        except (ValidationError, ValueError) as exc:
            raise HandoffError("Trail API returned an invalid researched place.") from exc

    async def create_route(self, start: ApiPlace, end: ApiPlace, stops: list[ApiPlace],
                           preferences: list[str]) -> ApiRoute:
        response = await self._request("POST", "/api/routes", (201,), allow_no_route=True, payload={
            "start": {"lat": start.lat, "lon": start.lon},
            "end": {"lat": end.lat, "lon": end.lon},
            "placeIds": [str(place.id) for place in stops], "preferences": preferences,
        })
        route = self._parse_route(response)
        self.check_stops(route, stops)
        return route

    async def get_route(self, route_id: str) -> ApiRoute:
        response = await self._request("GET", f"/api/routes/{quote(route_id, safe='')}", (200,))
        route = self._parse_route(response)
        if route.id != route_id:
            raise HandoffError("Trail API returned a different route.")
        return route

    @staticmethod
    def _parse_route(response: httpx.Response) -> ApiRoute:
        try:
            return ApiRoute.model_validate_json(response.content)
        except ValidationError as exc:
            raise HandoffError("Trail API returned an invalid route.") from exc

    @staticmethod
    def check_stops(route: ApiRoute, stops: list[ApiPlace]) -> None:
        if [place.id for place in route.places] != [place.id for place in stops]:
            raise HandoffError("Trail API returned different route stops.")
        for actual, expected in zip(route.places, stops):
            # Photo indexing can progress independently; canonical place/source data cannot change on replay.
            if actual.model_dump(exclude={"photos"}) != expected.model_dump(exclude={"photos"}):
                raise HandoffError("Trail API returned inconsistent place records.")
