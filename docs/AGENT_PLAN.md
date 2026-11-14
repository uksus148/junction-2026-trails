# Agent delivery and integration plan

This plan follows [CLAUDE.md](../CLAUDE.md), the
[contract review](CONTRACT_REVIEW.md), and the
[repository rules](REPOSITORY_RULES.md). It proposes remaining work; it does not
approve new endpoints, fields, tables, or Kafka event schemas.

## Current baseline

- PR #20 is merged: FastAPI chat, Valkey sessions, CORS, and storage timeouts.
- PR #26 is merged: Claude hiking intent, recent history, validation, and
  clarification for excessive stops/preferences. Live Claude remains unverified.
- HTTP chat still uses `{sessionId, message}` -> `{reply, places, routeId?}`.
- Spring Boot owns persisted places, routes, uploads, SQL, and Flyway migrations.
- [PR #27](https://github.com/uksus148/junction-2026-trails/pull/27) proposes
  GET /api/places, a Flyway places table, UUID IDs, and HTTP 400 Problem Details.
  It is pending owner review; place creation and route handoff remain separate.
- Mukhamed implements the agent; Murat owns the API/storage boundary; Daniil owns
  the frontend/chat boundary. Request both teammates for each agent PR.

## Sequential blocks

Finish review, fixes, applicable checks, and merge before starting another block.
Create branches from current main and keep each PR near 400 hand-written lines;
split a block further when needed. Reuse preserved work after checking its diff
against current contracts. Closed PRs #23–#25 are references, not a merge queue.

| Order | Block | Done when |
|---|---|---|
| 1 | Exa text research and Valkey caching, prepared in this PR | Sources retain URLs; repeated queries use a 24-hour cache; fixtures cover failures and credit conservation |
| 2 | Source-grounded place resolution and Nominatim geocoding | Names resolve to unique WGS84 coordinates with attribution; ambiguous results ask for clarification; geocoder rate limits and caches are tested |
| 3 | API ingestion and route handoff agreement | Murat, Mukhamed, and Daniil review example payloads, provenance, identifiers, ordering, and errors; accepted decisions are recorded in CLAUDE.md |
| 4 | Chat-to-route orchestration | Intent, research, geocoding, API persistence, and routing follow the agreed contract; frontend fetches and displays the returned persisted route |
| 5 | Licensed photos along the hike | Each displayed photo has author, license, sourceUrl, and coordinates; routes/photos follow the existing units and segment shapes |
| 6 | Gemini embeddings and pgvector ranking | Model/dimension and Flyway schema are agreed; preferences rank places/captions; repeated indexing is idempotent |
| 7 | Kafka upload processing and EXIF | photo.uploaded payload/storage access are agreed; consumer handles missing EXIF, duplicates, retries, and nearby trail association |
| 8 | Live integration and deployment | Tatras and a different live request work across the three services; sources, caching, failures, and deployment configuration are verified |

The route MVP is blocks 1–4 plus a live integration check; empty photo lists are
allowed until block 5. Day planning and personalization drafts remain deferred.

## Contract gates before runtime integration

These questions need the affected owners' answers, not unilateral agent changes:

- **Place ingestion: Murat + Mukhamed, with Daniil reviewing consumption.**
  `POST /api/places` currently accepts only name, lat, lon, and tags for manual
  creation. Agree how researched source URLs and OSM identity are persisted and
  deduplicated. Confirm API-issued identifier representation and success/error
  examples. Internal research evidence and geocoder IDs must not be sent as
  persisted `placeIds` until this mapping exists.
- **Routing: Murat + Mukhamed + Daniil.** Keep the baseline route request and
  response. Pass start/end coordinates and ordered intermediate API place IDs;
  avoid inserting duplicate endpoints as intermediate stops. Confirm how missing
  places, no walking route, and provider failures are represented. Return only an
  actual persisted routeId that the frontend can fetch.
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
- Agree reply-language behavior with Daniil before displaying clarification
  questions. Do not add day-mode fields to the existing chat request incidentally.
- Root .env supplies all services; empty secrets stay in .env.example. Keep cache
  TTLs, explicit timeouts, and fixture-based tests; do not retry paid calls blindly.
- Before the route MVP is accepted, run the Tatras request, a follow-up, and a
  different region with real services and the frontend. Check source links,
  repeated-query cache reuse, ambiguous places, and provider/storage failure paths.
  Fixture tests do not establish live model availability or end-to-end readiness.
