# trego. Agent delivery and integration plan

This plan follows [CLAUDE.md](../CLAUDE.md), the
[contract review](CONTRACT_REVIEW.md), and the
[repository rules](REPOSITORY_RULES.md). It proposes remaining work; it does not
approve new endpoints, fields, tables, or Kafka event schemas.

## Current baseline

- PR #20 is merged: FastAPI chat, Valkey sessions, CORS, and storage timeouts.
- PR #26 is merged: Claude hiking intent, recent history, validation, and
  clarification for excessive stops/preferences. Live Claude remains unverified.
- PR #28 is merged: Exa text evidence with source URLs and a 24-hour Valkey cache.
- PR #31 is merged after both teammates approved: source-grounded resolution,
  cached/rate-limited Nominatim, and bounded internal discovery. All 80 tests pass
  with fixtures at its merge; HTTP discovery and live geographic accuracy remain unverified.
- HTTP chat still uses `{sessionId, message}` -> `{reply, places, routeId?}`.
- Spring Boot owns persisted places, routes, uploads, SQL, and Flyway migrations.
- [PR #27](https://github.com/uksus148/trego/pull/27) is merged:
  GET /api/places, a Flyway places table, UUID IDs, and HTTP 400 Problem Details.
  API CORS and the client header fix (#29) are merged too. Place creation and
  route handoff remain separate.
- PR #33 is merged: manual creation returns a persisted UUID and server-owned
  `source: "manual"`. It does not implement research provenance/OSM ingestion.
- PR #34 is merged with both owner approvals. The accepted D1–D5 design is now
  published in CLAUDE.md. #35–#37 frontend follow-ups and #38 branding are merged.
- This increment adds the internal API adapter and route handoff with fixture
  validation; HTTP chat is still the baseline placeholder. API provenance writes
  and routing must be available before live use. Draft API work is not a baseline.
- Mukhamed implements the agent; Murat owns the API/storage boundary; Daniil owns
  the frontend/chat boundary. Request both teammates for each agent PR.

## Sequential blocks

Finish review, fixes, applicable checks, and merge before starting another block.
Create branches from current main. Mukhamed authorized combining coherent blocks
into PRs below 1000 changed lines to accelerate delivery; #31 combined providers
and internal orchestration in 766 changed lines including tests/docs. Review each
PR before starting the next. Reuse preserved work after checking its diff
against current contracts. Closed PRs #23–#25 are references, not a merge queue.

| Order | Block | Done when |
|---|---|---|
| 1 | Exa text research and Valkey caching, merged in #28 and #31 | Sources retain URLs; repeated queries use a 24-hour cache; mixed-result resilience is tested |
| 2 | Source-grounded resolution, Nominatim, and internal discovery, merged in #31 | A request yields ordered sourced findings with unique WGS84 coordinates and attribution; ambiguous/missing places stay unresolved; shared rate limits, caching, and overall deadlines are tested |
| 3 | API ingestion and route handoff agreement, accepted in #34 | Owner approvals are linked and D1–D5 decisions/examples are published in CLAUDE.md |
| 4 | Chat-to-route orchestration; internal persistence/readback prepared in this increment | Intent, research, geocoding, API persistence, and routing follow the agreed contract; frontend fetches and displays the returned persisted route |
| 5 | Licensed photos along the hike | Each displayed photo has author, license, sourceUrl, and coordinates; routes/photos follow the existing units and segment shapes |
| 6 | Gemini embeddings and pgvector ranking | Model/dimension and Flyway schema are agreed; preferences rank places/captions; repeated indexing is idempotent |
| 7 | Kafka upload processing and EXIF | photo.uploaded payload/storage access are agreed; consumer handles missing EXIF, duplicates, retries, and nearby trail association |
| 8 | Live integration and deployment | Tatras and a different live request work across the three services; sources, caching, failures, and deployment configuration are verified |

The route MVP is blocks 1–4 plus a live integration check; empty photo lists are
allowed until block 5. Day planning and personalization drafts remain deferred.

## Contract gates before runtime integration

These questions need the affected owners' answers, not unilateral agent changes:

- **Place ingestion: Murat + Mukhamed, with Daniil reviewing consumption.**
  D1/D2 are accepted: complete provenance, selected source URL, atomic OSM type/ID
  deduplication, first-write-wins, and authoritative API UUIDs. Murat must implement
  the extension; the merged manual handler ignores provenance and is not usable
  for research. The agent rejects a manual/non-URL source or an incorrect newly
  persisted source. No manual fallback or automatic POST retry is allowed.
- **Routing: Murat + Mukhamed + Daniil.** D3/D4 are accepted. The internal client
  submits returned endpoint coordinates and ordered/repeated intermediate UUIDs,
  validates the full created Route, then GETs the saved route before success.
  Only a complete 422 `no_hiking_route` problem is a normal no-route outcome;
  dependency failures remain errors. The HTTP chat still needs orchestration,
  clarification in the user's language, session handling and one overall deadline.
- **Photos and vectors: Murat + Mukhamed.** Agree entity keys, source metadata,
  caption storage, Gemini model, output dimension, and upsert semantics before
  Flyway migrations or vector writes. Do not infer an image license from a search
  result. Search evidence is not itself a Photo.
- **Uploads: Murat + Mukhamed.** Agree the photo.uploaded version, event/photo IDs,
  storage reference, supplied coordinates, and retry/acknowledgment semantics.
  Specify the fallback when EXIF location is missing and how processing is tracked.

Record each agreement with an example in CLAUDE.md and update the consuming
fixtures/types in the same review cycle. Public contract changes require the
affected owners' responses, even when GitHub's approval minimum is satisfied.

## Compatibility and acceptance checks

- Retain original source URLs throughout research, resolution, and persistence.
  API Place.source stays a string; Photo.sourceUrl is the photo's attribution URL.
- Coordinates in objects are WGS84 lat/lon; GeoJSON is `[lon, lat]`. Keep distance
  in km, ascent in m, and duration in minutes. Do not substitute straight lines or
  guessed IDs for a persisted hiking route.
- At chat wiring, handle IntentClarificationRequired as a normal reply with no
  routeId. Provider/storage failures remain honest errors; do not save a success
  for failed work. Set an overall request deadline, and validate required keys at
  startup only when the corresponding live feature is enabled.
- Daniil confirmed in PR #28 that replies and clarification questions follow the
  user's message language, while UI labels stay English. Implement that at chat
  wiring. Do not add day-mode fields to the existing chat request incidentally.
- PR #34 records required frontend integration work: retain chat endpoint Place
  records/sources alongside fetched routes, reset stale manual endpoints and
  derive both markers from the new track, deduplicate markers without losing
  repeated visits, hide empty segments, and parse structured errors. Daniil owns
  implementation in merged #35–#37; test a direct hike and chat after manual
  endpoint selection with live services before claiming route acceptance.
- Root .env supplies all services; empty secrets stay in .env.example. Keep cache
  TTLs, explicit timeouts, and fixture-based tests; do not retry paid calls blindly.
- Before the route MVP is accepted, run the Tatras request, a follow-up, and a
  different region with real services and the frontend. Check source links,
  repeated-query cache reuse, ambiguous places, and provider/storage failure paths.
  Fixture tests do not establish live model availability or end-to-end readiness.
