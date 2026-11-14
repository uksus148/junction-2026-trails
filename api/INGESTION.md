# Researched place ingestion

Merged PR #45 implements E1 of the [integration runbook](../docs/INTEGRATION_RUNBOOK.md)
on the existing `POST /api/places`, following the accepted D1/D2 contract in
[CLAUDE.md](../CLAUDE.md#accepted-sourced-place-and-route-handoff). Both affected owners
approved the final head, including the additional validation constraints below.
The isolated E4 backend live check passed; enabled chat and browser acceptance remain
separate gates.

## Follow a request

`CreatePlaceRequest` parses nullable HTTP values and rejects unknown top-level fields.
`NewPlace` retains name/tag normalization and coordinate invariants. Optional provenance
is inspected at the HTTP boundary to distinguish omission from explicit null and reject
lossy JSON-to-integer coercion. `ResearchProvenance` validates the reusable model invariants.

`PlaceService.create` owns a short READ COMMITTED write transaction:

1. Without provenance, save a normal JPA entity with source `manual`; return a new Place.
2. With provenance, run a parameterized native JPA INSERT with `ON CONFLICT DO NOTHING`.
3. Read the canonical entity by OSM type/id in a separate statement and map its snapshot.
4. Return `PlaceCreation(place, created)`. After commit, the controller selects 201 or 200.

The public Place still has its seven baseline fields; OSM identity stays internal. Selected
source URLs survive spatial search, repeated route visits and saved-route readback. The
API never fetches the submitted source URL or substitutes a manual record for bad provenance.

## Concurrency and schema tradeoffs

Flyway V3 adds nullable `osm_type`/`osm_id`, paired-null/type/positive-ID checks, and a unique
constraint on their pair. Manual and pre-existing rows remain valid and are not deduplicated.
The JPA entity and native spatial projections include the new columns. V1/V2 are unchanged.

The database arbitrates concurrent identities; a pre-read alone cannot guarantee uniqueness.
The insert reports whether this request created the row. At READ COMMITTED, a following
SELECT sees a winner that committed while the insert waited. If that writer rolls back,
the waiting insert can create its own row. Tests deliberately hold both situations open.

This costs an extra read and PostgreSQL-specific SQL. It avoids a caught unique violation
inside a rollback-only transaction and avoids no-op UPDATE/RETURNING writes, update triggers
and row churn on replay. No retry loop or independent JDBC persistence layer is introduced.
Metadata remains first-write-wins; refresh/history and cross-service rollback need separate designs.
See [PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

## Validation and review details

- Omitted provenance means manual creation; explicit null, partial/non-object provenance,
  unknown fields, non-HTTP(S) URLs and invalid OSM types/IDs produce 400 without writes.
- Unknown fields now include a submitted `source`; clients must use the documented shape.
- Implementation constraints accepted by Mukhamed in #45: positive signed-64-bit IDs (PostgreSQL
  bigint), no fractional/string coercion, and source URLs without embedded credentials or
  out-of-range ports. No name/tag/source truncation or new list limits are introduced.
- Write errors use Problem Details with `invalid_request` (400) or `storage_unavailable`
  (503). Expected connection/transaction/timeouts are mapped; programming/constraint bugs
  are not broadly reclassified. Existing GET validation retains its prior shape.

## Verification and environment

`cd api && mvn --batch-mode --no-transfer-progress clean verify` passed **185 tests**,
zero failures/errors/skips, on JDK 25 targeting Java 21. The 38 additional cases cover model
invariants, invalid payloads, first-write replay, commit/rollback contention, database checks,
manual compatibility, safe errors and researched-place-to-route readback.

After rebasing onto `440f69d` (#43/#44), the API tree matches the verified implementation.
The current agent's **202 fixture tests** pass. Its unmodified RouteHandoff/TrailsApi
also passed a real cross-service smoke against Spring, local PostgreSQL/Valkey and
fixture ORS: source retention, repeated visits, two saved route UUIDs, one provider
request and cache TTL. Created test rows were removed. Frontend previously passed
30 tests and a production build under Node 24; its tree is unchanged.

Live chat remains disabled; HTTP startup/session storage is not browser acceptance.
Use the root ignored `.env` for private configuration and follow the shared runbook.

### Live E4 follow-up

The configured Aiven PostgreSQL connection passed authenticated certificate/hostname
verification: PostgreSQL 18.7, PostGIS 3.6.4, vector 0.8.7. A temporary API applied V1-V3
and passed Hibernate validation in its own isolated cloud schema. One live ORS hike
returned 201 and a matching persisted GET. Repeating the same request after restarting
with an empty ORS key returned another saved UUID with the identical track from Aiven
Valkey; its TTL decreased from 86,399 to 86,388 seconds. Saved GET still worked after
deleting only this request's cache entry. Temporary schema/cache data was removed.

A separate current-main agent snapshot passed managed Aiven session storage and CORS
with live chat disabled. See the [shared E4 evidence](../docs/INTEGRATION_RUNBOOK.md#e4-live-backend-evidence)
and ignored `api/target/e4-live-report.json`. Claude/Exa credentials and account/model
access remain unverified. E1 is merged; the full browser/Tatras workflow remains pending.
