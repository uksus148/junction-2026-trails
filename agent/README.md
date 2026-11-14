# trego. Agent

The FastAPI `POST /api/chat` endpoint composes discovery, persisted route handoff,
language-aware replies, and Valkey history. Orchestration is opt-in and fixture-tested;
the default remains the baseline placeholder until the live prerequisites below pass.

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
uvicorn gopstop_agent.main:app --reload --log-config logging.json
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

The response follows `{reply, places:[Place], routeId?}`. Only a validated,
fetchable saved route supplies routeId; clarification has empty places and no ID.
Invalid payloads return FastAPI's `422`. Storage failures return `503` without
claiming the exchange was saved.

Run automated tests with `pytest`.

## Enable orchestration after integration preflight

E2 merged in #43 with both reviewers' approvals. Keep `AGENT_CHAT_ENABLED=false`
until researched ingestion (runbook E1) is reviewed/merged and E4 confirms credentials, model,
cache and service connectivity. Then set it to `true` in the root `.env` and restart.
The manual place handler is not a research fallback or capability probe.
See the [shared runbook](../docs/INTEGRATION_RUNBOOK.md) for the remaining gates.

Enabled startup checks that Claude/Exa keys and the model ID are nonblank; it makes
no provider requests and cannot prove account/model availability. Managed HTTP and
Valkey clients close on shutdown or failed startup. `create_app` accepts injected
clients/service for fixtures; the caller retains ownership of injected resources.

Chat loads the latest six exchanges, discovers places, clarifies incomplete or
excessive intent without ingestion, or calls the existing route handoff. Claude
phrases the known outcome in the latest user's language (conversation language
for a name/link-only follow-up). After generation, store the exchange before 200.
Only verified no-hiking-route becomes a normal reply. Provider/invalid-response
failures return 502, storage/cache failures 503, and deadlines 504, with safe detail.
Failed requests do not record success; already committed API data may survive
reply/storage failure or cancellation. Never automatically retry uncertain POSTs.

`AGENT_CHAT_TIMEOUT_SECONDS` defaults to 180 (maximum 300) and covers history,
discovery, handoff, reply generation and session storage. Existing shorter stage
limits still apply. `logging.json` enables stage elapsed time/outcome logs with a
random request trace and hashed session label, without message text, keys or raw
session IDs. These are internal diagnostics, not new public response fields.

## Intent extraction

`ClaudeIntentExtractor` uses Claude tool use and validates the internal
`{start, end, mustSee[], preferences[]}` result. It accepts recent session history,
keeps unknown endpoints null, and never asks the model for coordinates. The
adapter is connected through opt-in chat. Tests use HTTP fixtures, never live providers.

Blank endpoints become null, and blank list items are removed before validation.
If the result still exceeds five intermediate stops or twelve preferences,
`extract()` raises `IntentClarificationRequired` with a user-facing `question`.
Chat phrases that question as a normal reply rather than reporting a provider
outage; valid stops are not silently discarded. Transport, HTTP, and malformed
responses remain `ProviderError`; typed `ProviderTimeout` maps to 504.

Set `ANTHROPIC_API_KEY` in the root `.env`. `AGENT_ANTHROPIC_MODEL` follows the
team-plan default `claude-haiku-5-5`; select a model available to the team's account
before live testing. Each extractor request has a 20-second timeout by default;
its `timeout_seconds` argument overrides the supplied HTTP client's timeouts.
`AGENT_PROVIDER_TIMEOUT_SECONDS` supplies the setting for chat adapters.
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

`EXA_API_KEY` loads from the root `.env` as a masked secret. The adapter is used by
opt-in chat; it does not create API place IDs or infer photo licensing.
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
Up to three unique candidate chains run concurrently, retaining requested order;
all unfinished chains are cancelled and joined on failure or cancellation.

`CachedPlaceResolver` wraps Claude resolution in the production discovery factory.
Valkey retains validated results, including unresolved results, for 24 hours.
The versioned SHA-256 key covers the effective request: model, prompt/tool schema,
description and ordered source titles, URLs and text (only the three sent to Claude).
Changing any of those inputs requires a new resolution; credentials and session IDs
are excluded. Cache values contain only the typed resolution or null, never the
original request, keys or conversation history. Intent and replies remain per-message.

Hits do not refresh TTL. Expiry requires a fresh model call; malformed entries or
out-of-range source references refresh through the existing validated adapter.
A cache-read outage stops before the model; a write outage propagates after one
possibly paid call. Chat maps either to a safe 503 before ingestion. Failed or
cancelled provider work is not cached/retried. Concurrent first misses may still
make duplicate calls; this cache adds no distributed coalescing guarantee.
No new configuration is needed; it uses the existing Valkey client and deadlines.

Nominatim results, including empty/ambiguous ones, are cached for 24 hours. A
shared Valkey token gate holds through each request and for one second after it
finishes, including errors. Waiting has a deadline; ownership checks prevent an
expired worker from changing another's gate. Set `AGENT_NOMINATIM_USER_AGENT` to
identify the team; `AGENT_NOMINATIM_BASE_URL` can select a hosted service. Display
the returned OSM attribution when using these coordinates.

This is an internal result, not an API `Place`: it has OSM type/ID and source
evidence, but no persisted UUID or routeId. Enabled startup composes the factory;
researched ingestion and live integration remain prerequisites. Chat replies use
the user's language as agreed with Daniil in PR #28; UI labels remain English.

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
with an HTTP status of 502/503/504 and no remote body. Neither POST retries
nor redirects are followed; lost responses/deadlines may leave saved data behind.
There is no cross-service rollback or generated fallback route.

Root settings: `AGENT_API_BASE_URL` defaults to `http://localhost:8080`;
`AGENT_API_TIMEOUT_SECONDS` defaults to 20 seconds per API call and
`AGENT_HANDOFF_TIMEOUT_SECONDS` to 60 seconds for ingestion/create/readback together.
This internal deadline runs within the total chat deadline described above.

The factory is composed by opt-in chat. Routes/cache are merged in #39/#41; place
creation is still manual-only. Its ignored provenance/server-owned manual source
is rejected by this client. That rejection cannot undo an already committed place. Enable live use
only after researched ingestion and the required routing cache are reviewed;
this client is not a capability probe. Tests use HTTP fixtures, including repeats,
direct hikes, first-write replay, incomplete intent, provider/storage failures,
malformed responses, possible partial writes, and cancellation. HTTP chat tests
cover language/history, saved-route publication, failures, and every deadline stage.
The full agent suite passes 202 fixture tests. In two same-input discoveries/chat
requests, the three places require three resolution calls total, rather than six;
history, canonical places and saved-route readback still pass. This is call-count
evidence, not a measured live speedup. Live API/ORS, actual model language behavior,
and the browser flow remain unverified.

Before photos are enabled, agree the API/agent policy for incomplete attribution
or invalid photo URLs. The current strict photo model rejects an invalid photo
with the route; empty author/license or unsafe URLs must not silently become
verified credits. This increment leaves that future policy unchanged.
