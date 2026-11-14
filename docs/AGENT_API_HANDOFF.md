# Proposal: sourced place ingestion and chat-to-route handoff

**Status: proposed, awaiting Murat and Daniil's explicit agreement.** This is
block 3 of [the agent plan](AGENT_PLAN.md), following merged PR #31. It does not
enable HTTP discovery, implement API writes, or change the published contract.
Record accepted decisions in [CLAUDE.md](../CLAUDE.md) before implementation.

## Scope and ownership

Murat implements place persistence, deduplication, routing, and Flyway migrations.
Mukhamed implements the agent's API client and chat orchestration. Daniil checks
manual creation, route fetching, sources, and map consumption. Public `Place`,
`Route`, and chat response shapes stay as published; the proposed write extension
is optional provenance on `POST /api/places`. Day planning remains deferred.

The examples use synthetic UUIDs and OSM IDs, not verified live records. Coordinate
objects use WGS84 `lat`/`lon`; GeoJSON uses `[lon, lat]`.

## D1: one place write endpoint, optional research provenance

Keep manual creation exactly as the frontend sends it today:

```json
{"name":"My viewpoint","lat":49.15,"lon":20.07,"tags":["viewpoint"]}
```

Without `provenance`, the API creates a manual place with `source: "manual"`.
The agent supplies the same fields plus the selected research URL and OSM identity:

```json
{
  "name": "Skok waterfall",
  "lat": 49.1605,
  "lon": 20.0458,
  "tags": ["waterfall"],
  "provenance": {
    "sourceUrl": "https://example.org/hikes/skok",
    "osmType": "node",
    "osmId": 100000001
  }
}
```

The provenance object is all-or-nothing: an HTTP(S) source URL, `osmType` of
`node`, `way`, or `relation`, and a positive integer `osmId`. It is omitted for
manual places. Coordinates must be finite and within WGS84 bounds; names and tag
entries must be nonblank. Unknown fields and partial provenance return HTTP 400.
Agree any additional string/list size limits in the API implementation PR, and
mirror them in the agent before enabling writes; never silently truncate evidence.

For researched places, `Place.source` is the submitted research `sourceUrl`.
OSM identity is stored separately by the API and must not replace that URL or
become a public UUID. The agent retains the complete finding/evidence for its
current operation; this proposal persists the selected source, not search text
or every unselected result. Photos remain `[]` until the photo pipeline exists.

New manual or researched place: HTTP **201** and a complete `Place`.
This proposal does not add a place-by-ID GET endpoint or require a `Location`
header pointing to an unimplemented handler. Example response:

```json
{
  "id": "00000000-0000-4000-8000-000000000002",
  "name": "Skok waterfall",
  "lat": 49.1605,
  "lon": 20.0458,
  "tags": ["waterfall"],
  "photos": [],
  "source": "https://example.org/hikes/skok"
}
```

## D2: atomic deduplication and authoritative returned records

Deduplicate researched places on **both** `(osmType, osmId)` under a database
uniqueness constraint. Concurrent submissions must return one persisted UUID.
A replay returns HTTP **200** and the existing complete `Place`. Node 42 and
way 42 are different identities. Do not merge by name or rounded coordinates.

Use first-write-wins for canonical name, coordinates, tags, and selected source;
an import replay never overwrites an existing row. This preserves the original
source and avoids query-dependent updates. Metadata refresh or additional
provenance history would require a separate agreed workflow. The agent uses the
returned record, including its stored coordinates, for all downstream work.
Manual places have no OSM deduplication guarantee and may be created twice.

There is no cross-service rollback: if later routing fails, already saved places
remain reusable. Neither the API nor agent fabricates a successful route to hide
partial progress. API-owned migrations and race tests accompany implementation.

## D3: route ordering and persistence

Once every required finding is resolved, persist start, intermediate stops, and
end, reusing writes for identical OSM identities within the operation. Then send
the returned start/end coordinates and only intermediate UUIDs to the existing
`POST /api/routes` shape:

```json
{
  "start": {"lat": 49.119, "lon": 20.063},
  "end": {"lat": 49.179, "lon": 20.088},
  "placeIds": ["00000000-0000-4000-8000-000000000002"],
  "preferences": ["wild scenery"]
}
```

- API waypoints are start, each referenced place in array order, then end.
  Never sort UUIDs or treat the list as a set. Preserve explicitly requested
  repeated visits. Endpoints are not automatically inserted into `placeIds`.
- An empty `placeIds` is a direct hike. Agent intent currently allows at most
  five intermediate stops; the API must explicitly reject requests beyond its
  supported provider limit rather than drop stops.
- Resolve all referenced UUIDs before spending ORS credits. A well-formed but
  unknown UUID is an `unknown_place` error; malformed UUIDs are invalid input.
- API uses ORS `foot-hiking`, caches successful provider responses in Valkey for
  24 hours using a hash of all routing inputs, and persists the route before
  returning HTTP **201** with the full baseline `Route`.
- `Route.places` contains intermediate places in requested order, including
  repeated visits. Start/end are represented by track endpoints; add them as
  places only when explicitly requested as intermediate visits.
- `preferences` are retained verbatim as descriptive interests in this MVP.
  This proposal adds no ORS preference mapping or preference-based ranking;
  neither chat nor UI may claim they changed the track. Supported constraints
  or ranking come in a separately agreed implementation.
- Return an actual LineString from the provider, distance in km, ascent in m,
  and duration in minutes. Empty `segments` and empty photo lists are permitted
  before photos. No synthetic straight-line fallback is a hiking route.
- `GET /api/routes/{id}` returns HTTP **200** with the saved `Route`, or **404**
  for an unknown UUID. The same persisted route must be fetchable before chat
  returns its ID. Storage failure must not return a successful transient route.

Route POST is not made idempotent by this proposal. Repeating a completed request
may save another route, while its provider response can come from cache. The
agent performs no automatic POST retries, including after a lost response.
A failed response may follow a committed write; report the failure honestly.
Durable request idempotency would need a separate agreed key and replay policy.

## D4: errors that callers can interpret

New API write/route errors use `application/problem+json` with `type`, `title`,
`status`, `detail`, and an added stable `code` extension. Human-readable details
are English and exclude credentials/provider bodies. Do not parse English text
to choose chat behavior. Existing GET /api/places errors are unaffected.

| HTTP status | Proposed code | Meaning |
|---|---|---|
| 400 | `invalid_request` | Invalid fields, coordinates, UUID syntax, or unsupported waypoint count |
| 422 | `unknown_place` | A referenced place UUID does not exist |
| 422 | `no_hiking_route` | Provider returned a valid no-route result for these waypoints |
| 502 | `routing_provider_error` | Provider failed or returned malformed data |
| 503 | `storage_unavailable` | Required persistence is unavailable |
| 503 | `cache_unavailable` | Required routing cache is unavailable; no blind uncached retry |
| 504 | `routing_timeout` | Routing exceeded its deadline |
| 404 | `route_not_found` | GET of a missing saved route |

```json
{
  "type": "about:blank",
  "title": "No hiking route",
  "status": 422,
  "detail": "No walking route connects the requested waypoints.",
  "code": "no_hiking_route"
}
```

Only a verified `no_hiking_route` result becomes a normal chat reply asking for
different endpoints/stops. Provider or cache outages must not masquerade as
"no route". Agent-side HTTP errors retain FastAPI's existing `detail` envelope:
503 for storage/cache failure, 502 for dependency failures or an invalid API
response, and 504 for the overall deadline. An `unknown_place` after successful
ingestion is a dependency inconsistency, not an end-user validation failure.

## D5: chat completion, clarification, and frontend behavior

Keep `POST /api/chat {sessionId, message}` unchanged. Read recent history before
discovery. Missing/ambiguous findings and excessive intent limits produce a
normal HTTP **200** clarification in the user's message language, `places: []`,
and **no routeId**. Do not write partially resolved findings in that case.
The frontend already clears a previous route when a reply has no routeId.

For a complete discovery, ingest places, create the route, validate the API's
complete response, then record the exchange and return HTTP **200**. `places`
contains the returned persisted places in start/stops/end visit order, with
repeated UUIDs emitted once at their first occurrence for map markers. The route
request and `Route.places` still preserve repeated intermediate visits.

```json
{
  "reply": "Your hiking route via Skok waterfall is ready.",
  "places": [
    {"id":"00000000-0000-4000-8000-000000000001","name":"Štrbské Pleso","lat":49.119,"lon":20.063,"tags":[],"photos":[],"source":"https://example.org/hikes/start"},
    {"id":"00000000-0000-4000-8000-000000000002","name":"Skok waterfall","lat":49.1605,"lon":20.0458,"tags":["waterfall"],"photos":[],"source":"https://example.org/hikes/skok"},
    {"id":"00000000-0000-4000-8000-000000000003","name":"Rysy","lat":49.179,"lon":20.088,"tags":["peak"],"photos":[],"source":"https://example.org/hikes/end"}
  ],
  "routeId": "00000000-0000-4000-8000-000000000010"
}
```

The frontend fetches
`GET /api/routes/{routeId}` and displays that response, as it does today.
If saving the exchange fails after route creation, return 503; the saved route
and places may remain, but do not claim the exchange was saved. Failed operations
must not be appended as successful assistant replies.

Normal and clarification replies follow the user's message language; UI labels
stay English. Source links and visible OSM attribution must accompany geocoded
results. The baseline has no attribution field: Daniil should confirm displaying
the fixed OSM copyright link in the map UI. Neither photo licensing nor source
display should be inferred from a model-generated statement.

## Acceptance and rollout after agreement

1. **Murat + Mukhamed:** explicitly accept or amend D1/D2 (provenance shape,
   persisted source, atomic OSM deduplication, replay semantics) and D3/D4 (route
   order, preferences, codes, persistence, and failure behavior).
2. **Daniil:** confirm D1 manual creation compatibility, D3 route consumption,
   D4 error consumption, and D5 chat markers/language/attribution. Approval of
   internal discovery #31 did not approve these new write contracts.
3. Record the accepted decisions and examples in CLAUDE.md. Murat implements the
   API-owned writes/routes on that agreed contract; test concurrency, malformed
   inputs, repeated stops, no-route, outages, and saved-route retrieval.
4. Mukhamed's next agent implementation connects chat using fixtures for the
   accepted API. Enable live orchestration only when those API handlers exist;
   check required keys at startup and impose one total chat deadline. Address
   Daniil's #31 latency suggestion with bounded concurrent research/resolution,
   while keeping shared Nominatim serialization and cancellation guarantees.
5. Run the Tatras request, a follow-up, another region, ambiguity, and dependency
   failure across real services and frontend. Verify source links, OSM credit,
   UUID mapping, cached repeat requests, and retrieval of the same saved route.

Finish this PR's agreement and review before opening the next implementation PR.
An approval that omits a contract decision must not be presented as its acceptance.
