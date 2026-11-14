# Mukhamed's agent delivery plan

The baseline is [CLAUDE.md](../CLAUDE.md), with
[contract decisions](CONTRACT_REVIEW.md) and
[repository rules](REPOSITORY_RULES.md). This plan records implementation status;
it does not adopt the deferred day-planning proposal.

## Prepared implementation

| Plan task | Status |
|---|---|
| FastAPI chat and Valkey sessions | Implemented, including CORS, retention, and bounded waits |
| Claude intent extraction | Implemented with tool use, validation, and follow-up history |
| Exa place research with sources | Implemented with 24-hour Valkey caching |
| Nominatim/OSM geocoding | Implemented with caching, a shared 1 req/s gate, and clarification for ambiguous results |
| Exa photo and trail-description research | Pending; image author, license, and source must be verified |
| Gemini embeddings and pgvector ranking | Pending shared migrations and embedding-dimension agreement |
| Kafka photo.uploaded, EXIF, trail association | Pending event and storage contracts |
| Live chat → persisted places → hiking route | Pending API handoff and live credentials |

Forty-seven fixture-based tests pass on Python 3.12. No live provider credentials,
Aiven services, or paid API credits were used. See [agent setup](../agent/README.md).

## Merge order

1. PR #20, `feat/agent-core-mvp`: chat foundation and review-blocker fixes.
2. PR #23, `feat/agent-intent`: structured intent and session context.
3. PR #24, `feat/agent-place-search`: sourced research and geocoding.
4. `feat/agent-discovery-chat`: connect providers to the baseline chat endpoint.

Each PR builds on the previous branch. After each squash merge, retarget the next
PR to `main` and inspect its diff. Obtain independent approval before merging;
the frontend owner checks the chat boundary. This work does not merge any PR.

## Next integration decisions

- **Murat + Mukhamed: place ingestion.** The agreed `POST /api/places` payload has
  name, coordinates, and tags, but no provenance field. Decide how to persist Exa
  source URLs, map OSM identity to API identity, and avoid duplicate places. Record
  an agreed request/response example in CLAUDE.md before extending the contract.
- **Murat + Mukhamed: route handoff.** Confirm persisted identifier types and error
  codes. Use the existing route endpoint with start/end coordinates, ordered
  intermediate place IDs, and preferences. Return only the actual persisted route
  ID. Verify the frontend can fetch that route and draw its GeoJSON.
- **Murat + Mukhamed: vectors.** Agree Gemini model, vector dimension, entity keys,
  caption/source metadata, and upsert semantics. Murat supplies Flyway migrations;
  the agent generates embeddings and ranks candidates by user preferences.
- **Murat + Mukhamed: uploaded photos.** Agree event version, photo/event IDs,
  storage reference, supplied coordinates, and publication semantics. Then add an
  idempotent consumer with EXIF parsing, missing-EXIF handling, embeddings, nearby
  trail association, and a retry/failure policy.

## Live acceptance

Configure secrets in the ignored root `.env`, select an available Claude model,
and enable discovery. Run the Tatras request and a different judge-style request.
Check follow-ups, sources, cache reuse, and provider failure behavior. Once the API
handoff is ready, verify a persisted foot-hiking route and licensed photos in the
frontend. These live checks remain outstanding; passing fixtures is not proof of
live end-to-end readiness.
