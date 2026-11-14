# Hiking routes

This increment implements the baseline `POST /api/routes` and `GET /api/routes/{id}`.
Murat selected a provider interface plus an ORS adapter and accepted the route-side D3/D4
semantics from PR #34, with Valkey caching staged in the next focused PR. The cache-staging
amendment is recorded in that PR for the affected owners to confirm before integration.
The researched-place write extension is a separate implementation.

## Request flow and ownership

```text
RouteController
  -> RouteService
       -> RoutePersistence.resolveStops (short read transaction)
       -> RoutingGateway / OrsRoutingGateway (HTTP, no database transaction)
       -> RoutePersistence.save (short write transaction)
```

`routes/model` contains validated coordinates, a creation command, the provider-neutral track,
and response records. `routes/application` owns orchestration and the routing port.
`routes/integration` owns ORS configuration, authentication, wire formats, units, and error
translation. `routes/persistence` owns JPA entities, ordered associations, transaction boundaries,
and mapping to snapshots. `routes/web` owns HTTP parsing and Problem Details.

The service resolves all intermediate UUIDs before calling ORS. It passes start, intermediate
visits in their requested order, and end to the provider. It does not deduplicate visits or
sort UUIDs. Persistence rechecks referenced places before saving, so a place removed during
the provider call cannot become a successful transient route. A response is returned only
after the write transaction commits. No transaction spans the external HTTP call.

## Configure ORS

Set the root `.env` values, or the equivalent process environment:

```dotenv
ORS_API_KEY=
ORS_BASE_URL=https://api.heigit.org/openrouteservice
ORS_CONNECT_TIMEOUT=5s
ORS_READ_TIMEOUT=20s
```

The key is server-only. Its example stays empty, and the configuration's string representation
redacts it. A missing key prevents an outbound routing request and produces a safe
`routing_provider_error`; places endpoints and saved-route retrieval can still start and work.
Configure the key before live route creation. Credentials and provider response bodies are
not included in public errors.

The adapter calls `/v2/directions/foot-hiking/geojson`, requests elevation and metre units,
and converts provider metres to kilometres and seconds to minutes. It validates the actual
LineString and non-negative finite metrics. Height is retained as ascent, while the public
track uses two-dimensional `[longitude, latitude]` coordinates. Missing ascent or malformed
geometry is a provider failure, not a made-up zero or a straight-line fallback.

The default base URL follows [ORS's migration announcement](https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912).
See the official [response formats](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/requests-and-return-types)
and [error codes](https://giscience.github.io/openrouteservice/api-reference/error-codes).
The adapter performs no application-level retries and does not follow redirects.

## Create and retrieve

With the local database and API running, send persisted place UUIDs as intermediate visits:

```http
POST /api/routes
Content-Type: application/json

{
  "start": {"lat": 49.119, "lon": 20.063},
  "end": {"lat": 49.179, "lon": 20.088},
  "placeIds": [],
  "preferences": ["wild scenery"]
}
```

All four fields are required. Coordinates must be finite WGS84 values, and place IDs must
be UUIDs. Up to five intermediate visits are supported by this increment, matching the
current agent's intent limit; excessive requests are rejected before provider work. Empty
`placeIds` means a direct hike. Empty `preferences` is valid; supplied entries must be
non-null strings. Preferences are stored verbatim as descriptive interests and do not
change the ORS request or track in this increment.

A successful request returns HTTP **201 Created** with the baseline `Route`:
`id`, `geojson`, `distanceKm`, `ascentM`, `durationMin`, `places`, and `segments`.
`places` contains only intermediate visits, preserving order, duplicates, and source values.
Start/end markers use the returned track's endpoints, which can differ from requested
coordinates because the provider snaps them to its hiking graph. `segments` and photos
remain empty until the photo workflow is implemented.

`GET /api/routes/{id}` returns HTTP **200** and the saved route without another provider
request. Repeating POST can create another saved UUID. Callers must not automatically retry
POST after an uncertain response; a response failure can follow a committed write.

## Storage

`V2__create_routes.sql` adds `routes` and `route_places`. Existing place migrations are
unchanged. The route stores a PostGIS LineString, requested start/end points, provider
metrics, and descriptive preferences. The association's key is `(route_id, position)`;
the same place UUID can appear at multiple positions. Place foreign keys prevent dangling
visits. JPA fetches visits with an entity graph when loading a route; response mapping
finishes within the transaction while Open EntityManager in View remains disabled.

## Error contract

Errors use `application/problem+json` with English `detail` and a stable `code`.

| Status | Code | Meaning |
|---|---|---|
| 400 | `invalid_request` | Invalid or missing fields, UUID syntax, coordinates, or too many visits |
| 404 | `route_not_found` | Saved route UUID does not exist |
| 422 | `unknown_place` | A referenced place UUID does not exist |
| 422 | `no_hiking_route` | ORS explicitly reports no route or an unroutable point |
| 502 | `routing_provider_error` | Provider/network/configuration failure or malformed response |
| 503 | `storage_unavailable` | Storage connection or transaction failure |
| 504 | `routing_timeout` | Routing exceeded its configured deadline |

Only recognized ORS no-route codes on an appropriate client-error response become
`no_hiking_route`. Unknown errors, quota failures, authentication failures, and generic
provider 404s remain provider errors. SQL programming/constraint errors are not silently
classified as user mistakes. The future required cache will add `cache_unavailable`.

## Verify and review

```sh
cd api
mvn --batch-mode --no-transfer-progress clean verify
```

`RouteApiTest` uses real HTTP calls, the actual ORS adapter, a local JDK HTTP fixture server,
and disposable PostgreSQL 18/PostGIS. It checks ordered repeated visits, SQL geometry/SRID,
preferences, readback after the fixture provider fails, no provider call for unknown IDs,
timeouts, provider errors, storage failure, and malformed requests. Adapter unit tests cover
wire coordinates, metric conversion, malformed data, explicit no-route codes, and no retries.
Existing places and CORS tests remain in the suite. These fixture checks do not establish
live ORS availability or complete frontend/agent integration.

Latest local verification: **127 tests passed**, with no failures, errors, or skipped tests,
using JDK 25 with Java 21 as the compilation target. Of these, 54 cover the new route slice;
the 73 existing cases continue to pass. The implementation is published for early review in
[Draft PR #39](https://github.com/uksus148/trego/pull/39), which targets `main` after #33 merged.
See the PR's checks for the current Java 21 CI result. Cache staging remains subject to
affected-owner confirmation before this draft becomes ready for integration.

Review in this order: `RoutingGateway` and `RouteTrack`, `RouteService`, `RoutePersistence`
and `RouteEntity`, the V2 migration, `OrsRoutingGateway`, then the HTTP controller/advice
and the tests. The deferred cache and live-provider verification are tracked in the ignored
local architecture journal.
