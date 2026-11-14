# trego. Integration runbook

This is the shared execution and diagnostic guide for Murat, Mukhamed, and Daniil.
Read it before changing a service boundary, preparing an integration environment,
or reporting an end-to-end result. Last checked: November 14, 2026, against
`main` at `d4c91e9` (through merged #42), plus the E2 implementation under review.

## Authority and keeping the team aligned

- [CLAUDE.md](../CLAUDE.md) owns architecture, the accepted API contract, and team tasks.
- [The handoff agreement](AGENT_API_HANDOFF.md) explains accepted D1-D5 semantics;
  [the agent plan](AGENT_PLAN.md) tracks agent delivery.
- This runbook owns integration prerequisites, the delivery ledger, startup steps,
  and acceptance evidence. It does not independently approve contract changes.
- Follow [CONTRIBUTING.md](../CONTRIBUTING.md) and [repository rules](REPOSITORY_RULES.md).
  Every PR needs at least one independent approval; request affected component owners.
- Start from current main. Read the ledger and linked implementation PR before
  duplicating work. In each relevant implementation PR, update its ledger row,
  prerequisites, examples, and actual verification evidence together.
- For a shared behavior change, agree it with affected owners and update CLAUDE.md
  in the same review cycle. Link the agreement from this guide; do not maintain a
  competing contract or treat a private/local instruction file as team agreement.
- Rebase and recheck after dependent PRs merge. Preserve other owners' accepted
  sections when resolving conflicts. Tests with fixtures, merged code, and live
  acceptance are different milestones; report which one was actually reached.

## Current delivery ledger

Update this table when the relevant implementation merges or a live check runs.
Replace pending evidence with a PR/run link and tested revision; retain useful history.

| ID | Work | Owner | State at the checked revision | Evidence / next gate |
|---|---|---|---|---|
| B1 | Manual places and persisted hiking routes | Murat | Merged | #33, #39; real database/provider-fixture checks |
| B2 | Required 24-hour routing cache | Murat | Merged | #41; 147 API tests and Java 21/infra CI passed; live Aiven check pending |
| B3 | Discovery and internal API handoff | Mukhamed | Merged internally | #31, #40; fixtures do not enable HTTP chat |
| B4 | Frontend route/source/error compatibility | Daniil | Merged | #35-#37; live browser acceptance pending |
| E1 | Researched place ingestion and OSM deduplication | Murat | Not implemented | Blocks actual agent-to-API ingestion |
| E2 | HTTP chat orchestration and total deadline | Mukhamed | Prepared; awaiting review/merge | [#43](https://github.com/uksus148/trego./pull/43), tested `7b78c43`: 172 agent fixture tests pass; default disabled, E1/E4 block live use |
| E3 | Real-service frontend verification | Daniil | Pending | Disable mocks; verify direct/chat routes, sources, markers and errors |
| E4 | Integration environment and credentials | Murat coordinates; all owners verify clients | Unverified | Record selected host, service targets and successful connections privately |
| E5 | Full Tatras workflow | All three | Not run | Complete the acceptance matrix below on a recorded revision |

The current manual place endpoint ignores provenance and assigns `source: "manual"`.
The agent's researched-place client rejects that response after a possible committed
write. Do not use that path as a fallback or probe it repeatedly with live findings.

## Implementation responsibilities and merge gates

### E1: Murat - researched ingestion

Implement the [accepted D1/D2 contract](../CLAUDE.md#accepted-sourced-place-and-route-handoff)
on the existing place endpoint. Keep manual creation compatible. Validate complete
optional provenance; persist the selected research URL and separate OSM identity.
Use Flyway and database uniqueness for atomic first-write-wins replay: 201 for a new
Place, 200 for the authoritative existing Place, including concurrent requests.
Keep ordinary persistence in the agreed JPA organization; do not add another write endpoint.

Verify manual compatibility, invalid input without writes, source retention, concurrent
replay, node/way identity separation, and unchanged canonical metadata on replay.
Agree any additional limits with Mukhamed and record them in CLAUDE.md and both clients' fixtures.
Request Mukhamed for ingestion and Daniil for manual-client compatibility.

### E2: Mukhamed - HTTP orchestration

Wire the existing factories and adapters into chat with managed HTTP/Valkey resources:

```text
load recent history -> discover -> clarify OR persist handoff
                    -> phrase reply -> record exchange -> return reply, places, routeId?
```

Incomplete discovery produces a normal clarification without partial ingestion or
routeId. Reuse `RouteHandoff.persist()`, including its existing route readback; do not
duplicate that workflow or invent UUIDs. Return persisted display places while preserving
ordered/repeated intermediate visits in the route. Replies follow the user's language.

Handle verified no-route results as normal replies; propagate dependency/storage/deadline
failures through the accepted error policy. Failed work must not be stored as a successful
exchange. Session-storage failure after route creation returns 503; saved data may remain.
No automatic provider or API POST retries. Add one total chat deadline covering discovery,
handoff and session storage. Retain fixture injection for tests; verify live keys/model
availability before enabling live orchestration. Request Murat and Daniil for their boundaries.

The E2 branch implements this flow with injected HTTP fixtures and managed clients.
It also bounds discovery to three concurrent candidate chains, joins cancelled work,
and retains the shared Nominatim gate. `AGENT_CHAT_ENABLED=false` preserves baseline
behavior; setting it true validates nonblank keys/model at startup, not their live access.
The 180-second total deadline includes history and reply generation as well as the
stages above. No public fields, API schemas or Kafka events change.

### E3: Daniil - browser integration

Verify the existing real client and UI before adding more behavior. Disable mocks, use
the agreed URLs, and check loading/errors, fetched track geometry, endpoint/source retention,
reset of old manual endpoints, repeated visits, and hidden empty photo sections.
Report failures with request/status evidence. Request Murat for API-facing changes and
Mukhamed for agent-facing changes; presentation-only work follows normal component ownership.

E1 and E2 can be prepared against the accepted fixtures, following each owner's delivery
rules. Enable the full live flow only after E1 and E2 are reviewed and merged. Complete E3-E5
against the same main revision. These steps do not authorize merging unreviewed implementation.

## Environment profiles

**Proposed first diagnostic topology:** run API, agent and frontend on one computer,
with a dedicated test database on Aiven PostgreSQL and the team's Aiven Valkey service.
Murat coordinates access; each owner confirms their client. Record the selected topology
in the first test report. This document does not provision services or authorize new spending.

| Profile | Purpose | Data services |
|---|---|---|
| Isolated development | Fixture tests and debugging individual boundaries | Existing Docker PostgreSQL/PostGIS/pgvector and Valkey |
| Aiven integration | Verify actual challenge-platform connectivity and complete workflow | Team test targets on Aiven PostgreSQL and Valkey, over TLS |

Containers do not prove Aiven connectivity. Do not mix successful local fixture tests with
claims of live integration. Use isolated resources for outage/corruption experiments; do not
pause or globally flush the team's shared cache. Use a unique test session and record created IDs.

Prerequisites: Java 21, Maven, Node 24 (compatible with the committed frontend lockfile),
Python 3.12 with uv, and Docker for existing database-backed tests. All participants use the
same recorded main revision. For browser runs, reserve frontend 5173, API 8080, and agent 8000.
When services run on different machines, replace localhost with reachable URLs and update
both CORS configurations; localhost always means the caller's own machine.

### Root configuration

Copy [.env.example](../.env.example) to an ignored root `.env` if it does not exist;
preserve existing private values. Fill the selected profile privately. Commit only empty
secret examples. The table below is a configuration checklist, not a file containing credentials.

| Variable | Integration value / owner |
|---|---|
| `SPRING_DATASOURCE_URL` | Aiven JDBC URL for the selected test database; Murat |
| `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD` | Private database credentials; Murat |
| `SPRING_DATA_REDIS_URL`, `AGENT_VALKEY_URL` | Same selected Aiven Valkey target, `rediss://` with encoded credentials; Murat + Mukhamed |
| `API_VALKEY_CONNECT_TIMEOUT`, `API_VALKEY_COMMAND_TIMEOUT` | Existing defaults `2s`; Murat |
| `AGENT_VALKEY_CONNECT_TIMEOUT_SECONDS`, `AGENT_VALKEY_SOCKET_TIMEOUT_SECONDS` | Existing defaults `2`; Mukhamed |
| `ORS_API_KEY` | Valid server-side key; Murat |
| `ORS_BASE_URL` | Existing configured ORS endpoint; Murat verifies access |
| `ORS_CONNECT_TIMEOUT`, `ORS_READ_TIMEOUT` | Existing defaults `5s`, `20s`; Murat |
| `ANTHROPIC_API_KEY`, `EXA_API_KEY` | Valid private keys; Mukhamed |
| `AGENT_ANTHROPIC_MODEL` | Account-verified model ID; current default has no live verification |
| `AGENT_NOMINATIM_USER_AGENT` | Existing identifying team value; Mukhamed |
| `AGENT_API_BASE_URL` | `http://localhost:8080` |
| `AGENT_CHAT_ENABLED` | Default `false`; enable only after reviewed/merged E1/E2 and successful E4 preflight |
| `AGENT_CHAT_TIMEOUT_SECONDS` | E2 adds default `180`, maximum `300`; includes history through session save |
| `VITE_API_BASE_URL`, `VITE_AGENT_BASE_URL` | `http://localhost:8080`, `http://localhost:8000` |
| `VITE_USE_MOCKS` | `false`; restart Vite after changing |
| `API_CORS_ALLOWED_ORIGINS` | `http://localhost:5173`, unquoted comma-separated origins |
| `AGENT_CORS_ORIGINS` | `["http://localhost:5173"]`, JSON list |

Use PostgreSQL `sslmode=verify-full` with the appropriate Aiven CA certificate. Enable
PostGIS and vector in the selected database before Flyway; verify startup migrations and
Hibernate validation. Keep Valkey TLS peer verification enabled; convert an Aiven `valkeys://`
URI to the compatible `rediss://` scheme for these clients while retaining encoded credentials.
See [Aiven certificates](https://aiven.io/docs/platform/concepts/tls-ssl-certificates) and
[Valkey TLS](https://aiven.io/docs/products/valkey/howto/manage-ssl-connectivity).

Do not shell-source `.env`: JSON and Java-properties/dotenv escaping differ. Each service
uses its documented loader. Prefer injected environment variables for secrets with incompatible
escaping; keep local certificate paths outside shared configuration. Never put secrets in
VITE variables, screenshots, logs, issues, PR bodies, or CI. See the [route configuration guide](../api/ROUTES.md#configure-aiven-valkey).

### Timeout proposal - confirm in implementation review

The existing agent API timeout is 20 seconds, equal to ORS's read deadline before cache
and persistence overhead. Review this budget before live activation:

| Setting | Current value | Proposed diagnostic value | Status |
|---|---|---|---|
| `AGENT_API_TIMEOUT_SECONDS` | 20 | 30 | Supported setting; proposal, not applied |
| `AGENT_DISCOVERY_TIMEOUT_SECONDS` | 60 | 90 | Supported setting; proposal, not applied |
| `AGENT_HANDOFF_TIMEOUT_SECONDS` | 60 | 60 | Existing supported setting |
| `AGENT_CHAT_TIMEOUT_SECONDS` | E2 adds 180 | 180 | Implemented in the E2 branch; requires this PR's review/merge |

Murat/Mukhamed confirm provider, database/cache and total budgets; Daniil verifies browser
behavior. If hosted later, confirm proxy limits too. E2 adds the chat budget/switch
to the root example; existing API/discovery/handoff defaults remain unchanged.

## Startup and preflight

Start from the recorded main revision with the profile configured. The following are run
instructions, not evidence of E1 completion or live acceptance. Use separate terminals, each
initially at repository root; service-directory working paths matter for configuration loading.

```sh
cd api
mvn spring-boot:run
```

```sh
cd agent
uv sync --frozen --extra test
uv run --frozen uvicorn gopstop_agent.main:app --host 127.0.0.1 --port 8000 --log-config logging.json
```

```sh
cd frontend
npm ci
npm run dev -- --host localhost --port 5173 --strictPort
```

For isolated Docker development, follow [infra/README.md](../infra/README.md); use its
local connection values instead of the Aiven profile. Do not start an unused local database
and mistake it for the Aiven target.

Before sending paid/live requests, verify service startup, database migrations, authenticated
cache access/TTL, required provider keys/model access, and exact browser CORS origins. A
reachable agent OpenAPI page proves HTTP startup, not discovery or route readiness.
Leave the chat switch false during initial startup; after reviewed E1/E2 and the
preflight, enable it and restart before acceptance steps that exercise chat.

## Acceptance matrix

Run sequentially with a unique session label; keep all three owners available for failures.

| Step | Scenario | Required observation |
|---|---|---|
| 1 | Manual direct hike | Route POST 201, saved GET 200 with matching UUID/track, visible browser track |
| 2 | Manual saved intermediate place | Persisted place UUID and ordered visit survive route creation/readback |
| 3 | Chat with explicit start/end | Discovery -> sourced ingestion -> saved routeId -> browser GET/map; no placeholder |
| 4 | Tatras via Skok waterfall | Intermediate visit, endpoint metadata, source links, OSM attribution and actual hiking geometry |
| 5 | Repeat the exact route POST payload | New persisted UUID, provider track reused from 24-hour cache without another ORS call |
| 6 | Repeated OSM ingestion, including concurrency | Same canonical UUID and metadata, correct 201/200 behavior |
| 7 | Ambiguous request / excessive intent | Clarification without routeId or partial ingestion; stale browser route clears |
| 8 | Chat after different manual endpoints; repeated visits | Track endpoints replace old markers; repeated route visits remain; display markers deduplicate |
| 9 | No-route and isolated dependency failures | Expected distinction between normal no-route reply and honest 502/503/504 failures; no fake track/success |
| 10 | Follow-up in the same session; another region | Recent history is used and a different supported request completes across real services |

Use the canonical Tatras message: "I want to hike from Štrbské Pleso to Rysy via the Skok
waterfall. I love wild scenery." Confirm the actual location/source resolution rather than
assuming a fixture's coordinates. Start with a short known hiking segment for step 1.

Repeating chat text need not produce identical routing inputs. Prove cache reuse with the
same resolved payload and provider-call evidence. Sequential hits do not prove simultaneous
miss coalescing; that guarantee is not implemented. GET must remain independent of ORS/Valkey.

Existing API tests use real containers/provider fixtures; agent handoff tests use HTTP
fixtures. Current CI covers API and infrastructure, not the entire browser/agent workflow.
After the first successful run, owners can propose a fixture-backed cross-service regression
check. Live provider calls should remain deliberate and bounded, not an automatic CI dependency.

## Diagnostic report and completion

For each run, record: date/time with timezone, main SHA and pending branches, executor,
profile (local/Aiven), browser origin, sessionId, scenario and expected result. Add stage,
service, elapsed time, HTTP status/error code, persisted place/route UUIDs, browser request
evidence, and a redacted log excerpt. Record failing stage and owner before retrying; do not
automatically replay an uncertain POST. Previously committed data may survive a failure.

Record internal stages consistently: history, intent, research, geocoding, ingestion,
routing/cache, route readback, session save, and frontend route load. Correlate them with the
test session/timestamps and returned IDs without adding a required public header or API field.
With E2's logging configuration, the agent emits `trace`, hashed `session`, `stage`,
`elapsed_ms` and `outcome` (success or exception class), never provider bodies,
message text, credentials or raw session IDs. `routing_cache` times the API route
POST; use API evidence to distinguish an actual cache hit from a provider call.

E2 fixture evidence: `cd agent && uv run --frozen pytest -q` passes 172 tests.
The HTTP test exercises actual discovery/handoff factories, sourced API records,
saved-route readback, follow-up history, clarification/no-route, safe errors and
cancellation at every chat stage. No paid calls, live Aiven or browser acceptance
were run; this evidence does not complete E1, E3, E4 or E5.

E5 is complete only with reviewed E1/E2, a real fetchable route displayed in the browser,
retained research sources, a stored successful exchange, and evidence from the selected live
data services. Link the report from the completing PR and update this ledger. A placeholder
200, component CI pass, or an approved design alone does not complete E5.
