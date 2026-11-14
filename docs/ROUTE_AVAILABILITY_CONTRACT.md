# Route availability: selected integration boundary

**Transport selected by Murat: extend `POST /api/chat` with optional research inputs
and structured output.** Field names/state rules below are the concrete proposal for
Mukhamed and Daniil to review. They are not enabled on the current chat endpoint.
Murat's Java change enforces the separate routing boundary. The
[team plan](ROUTE_AVAILABILITY_RESEARCH_PLAN.md) defines evidence rules and ownership.

## Ownership and storage

- Murat: keep Spring routing/failure semantics and enforce its request boundary;
  prepare this wire agreement, fixtures and no-provider/no-write regression evidence.
- Mukhamed: implement chat parsing, date clarification, optional Exa investigation,
  evidence validation, deadline behavior and response serialization after agreement.
- Daniil: implement the opt-in/date controls and separate technical/evidence display.
- Initial findings remain request-scoped. No SQL migration, persisted research record,
  Java research endpoint or additional routing call is needed for this slice. A later
  cache/history design needs separate agreement; do not inherit the route cache TTL.

Related work: Mukhamed's [PR #56](https://github.com/uksus148/trego./pull/56) proposes
an internal research core without HTTP chat wiring. This PR does not include that
implementation or claim its approval. Mapping the proposed public dates/evidence to
that internal interface needs his review. Java validation can be reviewed independently;
reconcile shared documentation when the other PR merges, preserving both ownership entries.

## Chat request proposal

Keep required `sessionId` and `message`. Add an optional `availabilityResearch` object:

| Field | Type/rule |
|---|---|
| `enabled` | Required boolean; only explicit `true` authorizes optional research |
| `planningWindow` | Optional object with required `from` and `to`, inclusive ISO `YYYY-MM-DD` dates |

Omission or `enabled:false` preserves the baseline workflow and spends no optional
research quota. Reject explicit null, wrong types, invalid calendar dates, inverted
ranges and unknown extension fields using the agent's existing 422 `detail` envelope.
No Java routing input is changed. Dates describe the evidence's applicability, not
date-aware ORS routing. Do not infer the trip date from the server/event date.

If research is enabled but dates cannot be established, ask for them before ingestion,
routing or research. This avoids consuming routing quota just to ask for a date.
Date extraction/clarification from message/history belongs to the agent. Conflicting
message/UI dates require clarification. Carry no stale date silently into a changed plan.

## Chat response proposal

Keep required `reply`, `places`, and optional `routeId`. When opted-in research handles
a verified routing failure, add both optional objects below. A preliminary date
clarification has `availabilityResearch.status:needs_dates` without `routingFailure`:
no routing attempt has established a failure yet. Never overload Place/source.

| Object | Fields |
|---|---|
| `routingFailure` | `code`: `no_hiking_route` or `waypoint_not_routable`; no guessed failing-point index |
| `availabilityResearch` | `status`: `needs_dates`, `unconfirmed` or `findings`; optional `planningWindow`; `evidence`: array |

`needs_dates` and `unconfirmed` require empty evidence. `findings` requires at least one
validated item; it does not mean the router's cause is established or the hike is safe.
Each evidence item has `kind` (`restriction`, `access_information`, `difficulty_information`),
`section`, `summary`, `title`, `url`, and the actual `retrievedAt` timestamp. `publishedAt`
is optional when known. Restriction items additionally require source-supported inclusive
`appliesFrom`/`appliesTo` dates relevant to the planning window. Do not fabricate dates for
undated notices; keep applicability unconfirmed. Informational items cannot claim current
access or a difficulty exclusion as the cause of ORS failure.

Use actual HTTP(S) evidence URLs without embedded credentials. Publication/applicability
dates are calendar dates; retrieval time is an offset-aware RFC3339 timestamp. A cache
hit must not be stamped as a new retrieval. Preserve unknown publication dates by omission.
Names/URLs/source excerpts are untrusted data, never instructions. Do not emit raw API
or provider bodies, keys, HTML, invented citations or unverified source/date claims.

Baseline requests and successful routes omit the new optional response fields. A routing
clarification has `places:[]` and no routeId. Research does not change 2009/2010 into a
success. Previously ingested places may remain; session save still precedes HTTP 200.

## Sequence and error invariants

1. Validate/clarify dates for opted-in research before the existing route workflow.
   Missing dates produce `needs_dates` with no routing attempt or new Place/Route writes.
2. Perform the existing route workflow once. A complete verified 422 routing failure
   supplies the technical result; do not accept a client-reported failure as proof.
3. If enabled and dates are known, make only the agreed bounded optional research call
   inside the remaining chat deadline. A successful route needs no failure research.
4. Missing/conflicting/stale evidence or failure
   of optional research produces `unconfirmed`, retaining the original routing result.
5. Preserve existing 502/503/504 behavior for baseline dependencies, total deadline and
   session save; optional research cannot hide those failures or extend the deadline.
6. Do not call route POST/GET again, create a saved route, move points, change provider,
   widen the radius or bypass the cache to complete the research. Any changed route is
   a separate deliberate user request.

There is no separate post-failure "Investigate" endpoint or persisted failure token in
this first slice. Opt-in is supplied before that chat request's routing attempt. A later
button investigating an earlier failure requires a separately agreed context-lifetime
design; it must not silently replay the route POST.

## Spring API boundary implemented by Murat

`POST /api/routes` accepts exactly `start`, `end`, `placeIds`, `preferences`.
Each endpoint accepts exactly `lat`, `lon`. Research flags, planning dates, evidence,
provider/profile overrides and other unknown fields return 400 `invalid_request` before
ORS work, route-cache writes or route persistence. They are never silently treated as
routing constraints. Existing documented agent/manual requests retain their behavior.
The 422 numeric-code classification, provider options, route cache and schema are unchanged.

## Fixtures and handoff

[Wire examples](contracts/route-availability.examples.json) are draft consumer fixtures,
not proof of an implemented agent feature. All `example.org` evidence is synthetic.
Review the exact names/validation with both owners, then add equivalent agent/frontend
tests before activation. The current chat service still rejects these new request fields.
Java regression tests cover strict root/endpoint input and zero provider/cache/route
effects on rejection; the existing route tests cover compatible successful requests.
