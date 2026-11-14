# trego. Sourced place ingestion and chat-to-route handoff

**Status: accepted design in merged PR #34; runtime implementation incomplete.** This is
block 3 of [the agent plan](AGENT_PLAN.md), following merged PR #31. It does not
enable HTTP discovery, implement API writes, or change the published contract.
The accepted decisions are published in [CLAUDE.md](../CLAUDE.md#accepted-sourced-place-and-route-handoff).
Track current implementation gates and live evidence in the [integration runbook](INTEGRATION_RUNBOOK.md).

## Scope and ownership

Murat implements place persistence, deduplication, routing, and Flyway migrations.
Mukhamed implements the agent's API client and chat orchestration. Daniil owns
the frontend changes below: manual creation compatibility, route fetching,
source display, markers, and error presentation. Public `Place`,
`Route`, and chat response shapes stay as published; the accepted write extension
is optional provenance on `POST /api/places`. Day planning remains deferred.

The examples use synthetic UUIDs and OSM IDs, not verified live records. Coordinate
objects use WGS84 `lat`/`lon`; GeoJSON uses `[lon, lat]`.

## D1: one place write endpoint, optional research provenance

Keep manual creation exactly as the frontend sends it today:

```json
{"name":"My viewpoint","lat":49.15,"lon":20.07,"tags":["viewpoint"]}
```

The API's merged [manual-creation PR #33](https://github.com/uksus148/trego/pull/33)
builds on merged #32. The researched extension still needs API implementation;
manual creation alone is not provenance support. Keep the published normalization: all four baseline fields required, empty tags allowed,
names/tags trimmed, and duplicate tags removed in first-occurrence order with
case preserved.

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
current operation; this contract persists the selected source, not search text
or every unselected result. Photos remain `[]` until the photo pipeline exists.

New manual or researched place: HTTP **201** and a complete `Place`.
This contract does not add a place-by-ID GET endpoint or require a `Location`
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
  This contract adds no ORS preference mapping or preference-based ranking;
  neither chat nor UI may claim they changed the track. Supported constraints
  or ranking come in a separately agreed implementation.
- Return an actual LineString from the provider, distance in km, ascent in m,
  and duration in minutes. Empty `segments` and empty photo lists are permitted
  before photos. No synthetic straight-line fallback is a hiking route.
- `GET /api/routes/{id}` returns HTTP **200** with the saved `Route`, or **404**
  for an unknown UUID. The same persisted route must be fetchable before chat
  returns its ID. Storage failure must not return a successful transient route.

Route POST is not made idempotent by this contract. Repeating a completed request
may save another route, while its provider response can come from cache. The
agent performs no automatic POST retries, including after a lost response.
A failed response may follow a committed write; report the failure honestly.
Durable request idempotency would need a separate agreed key and replay policy.

## D4: errors that callers can interpret

New API write/route errors use `application/problem+json` with `type`, `title`,
`status`, `detail`, and an added stable `code` extension. Human-readable details
are English and exclude credentials/provider bodies. Do not parse English text
to choose chat behavior. Existing GET /api/places errors are unaffected.

| HTTP status | Code | Meaning |
|---|---|---|
| 400 | `invalid_request` | Invalid fields, coordinates, UUID syntax, or unsupported waypoint count |
| 422 | `unknown_place` | A referenced place UUID does not exist |
| 422 | `no_hiking_route` | Provider returned a valid no-route result for these waypoints |
| 422 | `waypoint_not_routable` | Issue #49 extension under review: a waypoint could not be matched to the hiking network within the provider radius |
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

The issue #49 extension, pending affected-owner review, distinguishes verified
`no_hiking_route` (ORS 2009) from `waypoint_not_routable` (ORS 2010). The former asks
for different endpoints/stops; the latter asks to verify coordinates or choose another
point. Neither establishes a closure or difficulty/seasonal cause. No radius increase,
substitution or automatic retry is introduced. See [live evidence](ROUTING_DIAGNOSTICS.md).
Provider or cache outages must not masquerade as
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

The frontend fetches `GET /api/routes/{routeId}`. Before #35, its successful-chat
path returned before retaining the chat's `places`; endpoint sources were lost,
and old manual endpoints could override or omit markers. Merged #35–#37 now
implement the follow-ups below. Verify them with live routes before acceptance.

**Frontend behavior to verify with live services:**

- Retain the chat's persisted `places` alongside the fetched route, including
  start/end records and their source URLs. Keep this display metadata separate
  from manually requested intermediate stops; do not turn endpoints into extra
  waypoints when a user subsequently builds a route manually.
- Apply the new route and its chat place metadata together after fetching the
  route. Derive both A and B marker coordinates from the first/last track
  coordinates; reset stale manual endpoint state when showing the chat route.
  Keep the endpoint Place metadata available for names and source links even if
  ORS snaps the track endpoints away from the stored place coordinates.
- Deduplicate displayed place markers by UUID while retaining repeated visits
  in the route request, `Route.places`, and segment order. Endpoint source
  records must remain accessible for a direct hike with no intermediate stops.
- Add source links to place popups or equivalent place details, so attribution
  is accessible without photos. Hide the along-the-way strip when `segments`
  is empty; it can appear once segments exist.
- Parse API Problem Details (`detail`, `code`) and FastAPI `detail` for useful
  error presentation instead of showing raw response JSON. Preserve the
  distinction between `no_hiking_route` and dependency failures from D4.

If saving the exchange fails after route creation, return 503; the saved route
and places may remain, but do not claim the exchange was saved. Failed operations
must not be appended as successful assistant replies.

Normal and clarification replies follow the user's message language; UI labels
stay English. Source links and visible OSM attribution must accompany geocoded
results. Daniil confirmed that the existing map attribution control displays
the OSM copyright link, so no attribution response field is proposed. Verify it
remains visible with the deployed map style. Neither photo licensing nor source
display should be inferred from a model-generated statement.

## Recorded review decisions

- Mukhamed owns the agent-side implementation of accepted D1–D5.
- [Daniil's owner response](https://github.com/uksus148/trego/pull/34#pullrequestreview-5901154716)
  explicitly accepts D1, D3, D4, and D5 and takes the frontend follow-ups; his
  [final re-review](https://github.com/uksus148/trego/pull/34#pullrequestreview-5903913530)
  confirms that agreement and the clarified tasks. This
  agreement does not mean those frontend changes are implemented. D2 remains an
  API/agent decision; do not infer Daniil's acceptance of it from that response.
- [Murat's final owner response](https://github.com/uksus148/trego/pull/34#pullrequestreview-5904059886)
  explicitly accepts D1–D4 as his personal API/storage decision and approves the
  clarified D5 ownership and scenarios. This supersedes the earlier technical
  COMMENT and pending-decision wording; it is not inferred from that COMMENT.

The shared design is accepted and recorded in CLAUDE.md. API handlers, agent
integration, and live acceptance still need implementation/review. Frontend
follow-ups #35–#37 are merged; their fixture checks are not live route acceptance.

## Implementation and acceptance after agreement

1. **Murat + Mukhamed:** D1–D4 agreement is recorded above and in CLAUDE.md.
   Murat owns API implementation and Flyway; Mukhamed owns the agent client.
   Further shared changes need affected-owner agreement.
2. **Daniil:** D1/D3/D4/D5 acceptance and the clarified D5 frontend work are
   recorded above. Implementation landed in #35–#37; the scenarios below still
   require live verification. Approval of discovery #31 alone did not approve writes.
3. The accepted decisions and examples are in CLAUDE.md. Murat implements the
   API-owned writes/routes on that agreed contract; test concurrency, malformed
   inputs, repeated stops, no-route, outages, and saved-route retrieval.
4. Mukhamed's E2 implementation connects chat against accepted fixtures, with
   managed clients, language-aware replies/history, a total deadline, and up to
   three concurrent candidate chains. Nominatim serialization and cancellation
   remain enforced. It is disabled by default and awaits review/merge; enable
   only after E1 and live preflight. Track evidence in the integration runbook.
5. Daniil implemented the D5 frontend follow-ups in #35–#37. Before live
   acceptance, test
   a direct chat hike with `placeIds: []`, `Route.places: []`, and no photos:
   show both track endpoint markers and both endpoint research sources, without
   an empty gallery. Test a chat route after choosing different manual endpoints:
   markers move to the new track and old manual coordinates do not take priority.
   Also test repeated intermediate UUIDs: one place marker per UUID, ordered
   repeated route visits, and source links for every returned place. Test
   structured API/FastAPI errors and a clarification that clears the prior route.
6. Run the Tatras request, a follow-up, another region, ambiguity, and dependency
   failure across real services and frontend. Verify source links, OSM credit,
   UUID mapping, cached repeat requests, and retrieval of the same saved route.

Finish each implementation PR's review and merge before starting another block.
Agreement must not be presented as completed implementation or live acceptance.
