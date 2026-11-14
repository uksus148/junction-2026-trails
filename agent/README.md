# trego. Agent

The FastAPI `POST /api/chat` endpoint validates requests, stores exchanges in Valkey,
and returns a placeholder. Internal discovery and route handoff are available for
fixture-tested composition; HTTP orchestration is not enabled yet.

## Run locally

From this directory, create and activate a virtual environment, then install the service and test dependencies:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

For reproducible installs with uv, run `uv sync --frozen --extra test` instead;
`uv.lock` is committed alongside `pyproject.toml`.

Settings load from the repository root `.env` and process environment. Set `AGENT_VALKEY_URL` to a Redis-compatible Valkey URL; when it is unset, the service also accepts the shared `SPRING_DATA_REDIS_URL` variable. The default is `redis://localhost:6379/0`. `AGENT_SESSION_TTL_SECONDS` defaults to 86400 (one day), and `AGENT_SESSION_MAX_MESSAGES` defaults to 200 messages per session (must be even so history is retained in complete user/assistant exchanges). Start the API with:

```sh
uvicorn gopstop_agent.main:app --reload
```

Browser calls are allowed from `http://localhost:5173` by default. Set
`AGENT_CORS_ORIGINS` to a JSON list of frontend origins for deployment, for example
`["https://trails.example.org"]`. Only POST and the Content-Type request header are
allowed. Valkey connection and read/write timeouts default to two seconds each;
configure `AGENT_VALKEY_CONNECT_TIMEOUT_SECONDS` and
`AGENT_VALKEY_SOCKET_TIMEOUT_SECONDS` to change them. Timeouts return the same 503
as connection failures. These settings are listed in the root `.env.example`.

If port 5173 is busy, Vite may start the frontend on 5174. Check the URL printed
by Vite and add that exact origin to `AGENT_CORS_ORIGINS` in the root `.env`, for
example `AGENT_CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]`.
Restart the agent after changing this setting so the browser preflight succeeds.

## Chat contract

```http
POST /api/chat
Content-Type: application/json

{"sessionId":"demo-session","message":"I want to hike from Štrbské Pleso to Rysy via Skok waterfall."}
```

The response follows the shared contract: `{ "reply": string, "places": [] }`, with `routeId` omitted until a route is available. Invalid payloads return FastAPI's `422` validation response. If Valkey is unavailable, the service returns `503` and does not claim that the message was saved.

Run automated tests with `pytest`.

## Intent extraction

`ClaudeIntentExtractor` uses Claude tool use and validates the internal
`{start, end, mustSee[], preferences[]}` result. It accepts recent session history,
keeps unknown endpoints null, and never asks the model for coordinates. The
adapter is tested with HTTP fixtures and is connected to chat in the next
discovery block. There are no live provider calls in the test suite.

Blank endpoints become null, and blank list items are removed before validation.
If the result still exceeds five intermediate stops or twelve preferences,
`extract()` raises `IntentClarificationRequired` with a user-facing `question`.
The chat integration must return that question in its normal reply rather than
reporting a provider outage; valid stops are not silently discarded. Transport,
HTTP, and malformed-response failures remain `ProviderError`. HTTP chat wiring
is outside this block, so its current behavior is unchanged.

Set `ANTHROPIC_API_KEY` in the root `.env`. `AGENT_ANTHROPIC_MODEL` follows the
team-plan default `claude-haiku-5-5`; select a model available to the team's account
before live testing. Each extractor request has a 20-second timeout by default;
its `timeout_seconds` argument overrides the supplied HTTP client's timeouts.
`AGENT_PROVIDER_TIMEOUT_SECONDS` supplies the setting for the later chat wiring.
No automatic paid retries are performed. Live account/model availability has not
been verified.

## Exa research adapter

`ExaSearch` provides internal text evidence as `{title, sourceUrl, text}`. It keeps
up to three results, preserves source URLs, and caches successful responses,
including empty results, in Valkey for 24 hours. Cache keys hash the full search
request. Missing titles fall back to the source URL; missing text becomes empty.
Mixed responses keep the valid sources; a non-empty response with no usable
source is a provider error. Corrupt cache entries are refreshed. A failed cache
read stops before Exa. A failed cache write propagates after Exa has already
consumed credits; the adapter does not retry the call. Provider errors are not
cached or retried, and request timeouts are explicit.

`EXA_API_KEY` loads from the root `.env` as a masked secret. The adapter is not yet
wired into HTTP chat and does not create API place IDs or infer photo licensing.
See [the delivery plan](../docs/AGENT_PLAN.md) for the next blocks and the owner
agreements required before API persistence and route integration.

## Source-grounded place discovery

`create_discovery(client, cache, settings)` builds `PlaceDiscovery` using the root
settings and validates the Claude/Exa keys when explicitly enabled by a caller.
`await discovery.discover(message, history)` runs intent, Exa, Claude place
resolution, and Nominatim as one bounded internal pipeline. The default total
deadline is 60 seconds (`AGENT_DISCOVERY_TIMEOUT_SECONDS`); provider timeouts use
`AGENT_PROVIDER_TIMEOUT_SECONDS`. Tests do not call live providers.

The result retains start/end findings, ordered stops, all research sources, and
the selected source with each uniquely geocoded place. `unresolved` and
`missing_endpoints` support clarification; `ready_for_handoff` is false while any
required location is missing. Repeated targets reuse work without removing visits.
`IntentClarificationRequired` propagates before research for over-limit intent.

Nominatim results, including empty/ambiguous ones, are cached for 24 hours. A
shared Valkey token gate holds through each request and for one second after it
finishes, including errors. Waiting has a deadline; ownership checks prevent an
expired worker from changing another's gate. Set `AGENT_NOMINATIM_USER_AGENT` to
identify the team; `AGENT_NOMINATIM_BASE_URL` can select a hosted service. Display
the returned OSM attribution when using these coordinates.

This is an internal result, not an API `Place`: it has OSM type/ID and source
evidence, but no persisted UUID or routeId. The factory does not run at application
startup yet; HTTP chat behavior is unchanged. The handoff design is accepted;
researched ingestion and live integration remain implementation/acceptance work. At chat wiring, use the user's message language
for normal and clarification replies, as agreed with Daniil in PR #28; UI labels
remain English.

## Persisted route handoff

The [accepted D1–D5 contract](../CLAUDE.md#accepted-sourced-place-and-route-handoff)
is published after both owner approvals in #34. `create_handoff(client, settings)`
composes `RouteHandoff`; `await handoff.persist(discovery_result)` accepts only a
complete resolved discovery. It ingests sourced places through the API, reuses
OSM type/ID writes within the operation, and uses the authoritative UUIDs and
coordinates returned by the API. It never invents IDs or drops repeated visits.

The route POST contains only intermediate UUIDs in visit order. The result is
validated as a full Route and then fetched by ID; mismatched IDs/stops, malformed
geometry, invalid units/coordinates, or a failed readback produce an error.
`HandoffResult` holds the saved route, persisted place records deduplicated only
for display, and OSM attribution. Original discovery evidence is left intact.

Only a complete 422 Problem Detail with `code: "no_hiking_route"` raises
`NoHikingRoute` for a normal chat reply. Other failures raise safe `HandoffError`
with a future HTTP status of 502/503/504 and no remote body. Neither POST retries
nor redirects are followed; lost responses/deadlines may leave saved data behind.
There is no cross-service rollback or generated fallback route.

Root settings: `AGENT_API_BASE_URL` defaults to `http://localhost:8080`;
`AGENT_API_TIMEOUT_SECONDS` defaults to 20 seconds per API call and
`AGENT_HANDOFF_TIMEOUT_SECONDS` to 60 seconds for ingestion/create/readback together.
This internal deadline does not replace a future total chat deadline covering
discovery, handoff, and session storage.

The factory is not wired into HTTP chat. Routes are merged in #39; place
creation is still manual-only. Its ignored provenance/server-owned manual source
is rejected by this client. That rejection cannot undo an already committed place. Enable live use
only after researched ingestion and the required routing cache are reviewed;
this client is not a capability probe. Tests use HTTP fixtures, including repeats,
direct hikes, first-write replay, incomplete intent, provider/storage failures,
malformed responses, possible partial writes, and cancellation. Live API/ORS,
locale-aware replies, and the frontend route flow remain acceptance work.

Before photos are enabled, agree the API/agent policy for incomplete attribution
or invalid photo URLs. The current strict photo model rejects an invalid photo
with the route; empty author/license or unsafe URLs must not silently become
verified credits. This increment leaves that future policy unchanged.
