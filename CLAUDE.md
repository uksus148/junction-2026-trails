# GOPSTOP.PROTOCOL — Junction 2026

An AI hiking navigator. Users describe what they want to see in chat or mark places on a map
(castles, waterfalls, scenic views) and receive a walking route from A to B through those places,
with real photos of views along the way and links to their sources.

This file is the team's single source of truth for developers and AI assistants. Update it whenever a decision is made.

## Project language and branches

- English is the project language. Write repository files, code comments, documentation, commit messages, PR titles, descriptions, and reviews in English.
- Use descriptive branch names such as `feat/places-bbox`, `fix/route-distance`, `docs/api-contract`, `infra/local-database`, or `chore/dependencies`.
- The `codex/` prefix is prohibited for new branches.
- Keep PRs small, about 400 hand-written lines; generated files such as lockfiles don't count. Split larger work into stacked PRs that each build and pass tests, and keep a dependency manifest and its lockfile in the same PR so `npm ci` works on every revision.
- Follow [CONTRIBUTING.md](CONTRIBUTING.md) and the [repository rules](docs/REPOSITORY_RULES.md).
- Review this file before changing the code. Follow Murat's current task and agree shared contract changes with the affected developers.

## Challenges (draft submitted on November 13 at 23:59)

- **Main:** The Internet Butler / Your Personal Assistant — **Exa**. Judging considers using Exa for information outside the model's training data, value for a specific group (hikers and tourists), visible sources, originality, and a demo that handles **live requests from judges**.
- **Tech:** Best Use of **Aiven**. Meaningful use 40%, technical implementation 30%, product impact 20%, creativity 10%.
- Optional Cloudinary submission, if photo uploads use it. Separate form at https://cld.media/hackathon-survey.

## Junction requirements

- Write all code during the hackathon, which starts November 13 at 19:30. The repository must be **public** and use the **MIT** license.
- **Final submission is Sunday, November 15 at 10:00.** Change Draft to Final. Late submissions are rejected.
- The video pitch must be **at most 2:00**, with a public YouTube or Vimeo link. Provide the pitch deck as a PDF.
- **All three team members must attend peer review on Sunday, 10:30–13:00**, to remain eligible for the main prize.
- The top five teams get a three-minute pitch and three minutes of questions.

## Budget

Use partner credits and free tiers. All times in this document are local to the event in Helsinki.

| Need | Provider | Team cost |
|---|---|---|
| Place and photo web search | **Exa**, $50 × 3 = $150 | Partner credits |
| Agent LLM | **Claude**, $20 × 3, `claude-haiku-5-5` by default and `claude-sonnet-5-5` for planning | Credits |
| Embeddings | **Gemini API** | Free credits or free tier |
| Coding assistance | Codex $100, Claude Code | Credits |
| Database | **Aiven PostgreSQL** Free with PostGIS and pgvector | Free |
| Cache | **Aiven Valkey** Free | Free |
| Events | **Aiven Kafka**, minimal plan using $50 credits, turn off while unused | Credits |
| Observability, stretch goal | Aiven ClickHouse if credits remain | Credits |
| Map | MapLibre GL and OpenFreeMap tiles | Free, no key |
| Points of interest | OSM Overpass API, `historic=castle`, `waterway=waterfall`, `tourism=viewpoint`, `natural=peak` | Free |
| Hiking routes | OpenRouteService `foot-hiking`, approximately 2,000 requests per day | Free API key |
| Photos | Wikimedia Commons API, Mapillary, Exa. User uploads may use Cloudinary Free | Free |
| API and agent hosting | Aiven Runtime if credits suffice, Modal $100 as a fallback | Credits |
| Frontend hosting | Cloudflare Pages or Vercel Free | Free |

Excluded providers are Oxylabs, which requires a card and subscription, paid video-generation plugins, and Verda/Featherless GPU services.

Cache Exa and routing responses in Valkey. Use a query hash as the key and a 24-hour TTL. Use fixtures during development to conserve live API credits.

## Architecture

```text
frontend (React + Vite + Tailwind + MapLibre)
   | REST
   +---> api (Spring Boot, Java)  — places, routes, uploads, PostGIS queries, ORS routing
   |       | Kafka: photo.uploaded, route.requested
   +---> agent (FastAPI, Python) — chat, LLM intent extraction, Exa, embeddings, photo pipeline
           |
   Aiven PostgreSQL (PostGIS + pgvector), Aiven Valkey (cache and chat sessions), Aiven Kafka
```

### Required demo scenario

High Tatras. “I want to hike from Štrbské Pleso to Rysy via the Skok waterfall. I love wild scenery.”

The agent finds Skok and Rysy, builds a route through them, and displays the track, places, and photos for each section with sources. A judge must also be able to enter a different request. Keep the region configurable, with deeper testing for the Tatras.

### API contract

Agree changes with the affected developers and record them here.

- `POST /api/chat` `{sessionId, message}` → `{reply, places:[Place], routeId?}` (agent)
- `GET /api/places?bbox=minLon,minLat,maxLon,maxLat&tags=castle,waterfall` → `[Place]` (api)
- `POST /api/places` `{name, lat, lon, tags[]}` for manual place creation (api)
- `POST /api/routes` `{start:{lat,lon}, end:{lat,lon}, placeIds[], preferences[]}` → `Route` (api)
- `GET /api/routes/{id}` → `Route`
- `POST /api/photos` multipart `{file, lat, lon}` publishes Kafka event `photo.uploaded`
- `Place = {id, name, lat, lon, tags[], photos:[Photo], source}`
- `Photo = {url, thumbUrl, author, license, sourceUrl, lat, lon}`
- `Route = {id, geojson(LineString), distanceKm, ascentM, durationMin, places:[Place], segments:[{fromKm,toKm,photos:[Photo]}]}`

### Proposed sourced place and route handoff — not agreed yet

[docs/AGENT_API_HANDOFF.md](docs/AGENT_API_HANDOFF.md) proposes optional research
provenance for place creation, atomic OSM deduplication into persisted UUIDs,
ordered route handoff, error codes, and chat completion. Daniil explicitly
accepted D1/D3/D4/D5 in [his PR #34 response](https://github.com/uksus148/junction-2026-trails/pull/34#pullrequestreview-5901154716)
and owns the recorded frontend integration tasks. Murat's personal API/storage
decision is still pending; the technical COMMENT from his account does not
approve the architecture. Required owner agreement remains a gate to implementation.
The proposal does not change the published API contract above. Move accepted
decisions here after review; PR #31's internal discovery approval is not write
contract agreement.

### Proposed extension: personalization and day plan — not agreed yet

Discussed in [docs/CONTRACT_REVIEW.md](docs/CONTRACT_REVIEW.md). Move items into the contract above only after the owners agree.

- Chat request adds `mode: 'route'|'day'` and `preferences`; the response adds `mode`, `itineraryId?` and `preferencesPatch?` with preferences understood from the message.
- `Preferences = {interests[], dislikes[], pace: 'relaxed'|'normal'|'intense', maxWalkKm, budget: 0-3, avoidCrowds}`
- `Place` gains optional `dwellMin`, `priceLevel` (0-3), `crowdLevel` (0-2) and `openingHours {open, close}`.
- `POST /api/itineraries` `{start, placeIds[], preferences, startTime, endTime}`, `GET /api/itineraries/{id}`, and `POST /api/itineraries/{id}/replan` `{now, location?, skipPlaceIds[], donePlaceIds[], preferences?}` return an `Itinerary`.
- `Itinerary = {id, route, start, startTime, endTime, resumeAt, candidates, preferences, stops, dropped:[{place, reason}], walkKm}`; each stop has `arriveAt`, `leaveAt`, `travelMin`, `travelKm`, `travelMode: 'walk'|'transit'` and `status: 'planned'|'done'|'skipped'`.
- Drop reasons: `dislike`, `budget`, `closed`, `no_time`, `walk_limit`, `skipped_by_user`. Legs over 2.5 km use transit (18 km/h plus 8 minutes) and do not count toward the walking limit. Replanning never starts before `startTime`.
- Daniil has a tested reference implementation of the planner and intent parsing, ready to submit with the frontend. Demo request: “Plan my day in Bratislava from 10:00, no museums please, I hate crowds.”

### Repository layout

```text
/frontend — Daniil
/api      — Murat
/agent    — Mukhamed
/infra    — local Docker Compose and database extension initialization
```

Application tables are managed by Flyway migrations in `api`. Keep credentials in a local `.env`, which is ignored by Git. Commit `.env.example` with empty secret fields. Every service, including the frontend, reads the single root `.env`.

### Java API organization

The Spring Boot API is a single Maven module. Group Java packages by feature under `io.junction.trails`. The current `places` feature separates HTTP handlers and error mapping in `web`, transaction boundaries and workflows in `application`, framework-independent values and response data in `model`, and JPA entities and repositories in `persistence`. Keep entities out of HTTP responses. Use Spring Data JPA and Hibernate Spatial for ordinary persistence; native queries preserve PostGIS-specific search behavior. JDBC remains available for complex queries when it offers a concrete benefit. Future `routes` and `photos` features follow the same feature-based organization. Tests mirror production package paths. Flyway owns the schema; Hibernate validates it and Open EntityManager in View is disabled. See the [API code map and review order](api/README.md#code-map).

Shared Spring MVC configuration applies CORS to `/api/**` for GET and POST with Content-Type. `API_CORS_ALLOWED_ORIGINS` configures a comma-separated list of exact frontend origins; the default is `http://localhost:5173`. See the API README for local and deployed frontend configuration.

Use Lombok `@RequiredArgsConstructor` for constructor-based dependency injection with final fields, without `@Autowired` on the single generated constructor. Bind configuration values to immutable properties objects when injecting them into components. Use Lombok for ordinary getters, setters where mutation is appropriate, and boilerplate constructors in non-Spring classes too. Keep invariant checks, defensive copies, derived accessors, and other behavioral constructor/accessor logic explicit. JPA entities may use a protected Lombok `@NoArgsConstructor`.

### Frontend

- React 19, TypeScript, Vite 8, Tailwind 4 and MapLibre 6 with OpenFreeMap tiles. The UI is in English.
- Runs on in-browser mocks by default (`VITE_USE_MOCKS=true`). Set it to `false` and fill `VITE_API_BASE_URL` and `VITE_AGENT_BASE_URL` to use the real services.
- Demo and fallback photos come from Wikimedia Commons geosearch: free, CORS enabled, with author and license.
- MapLibre 6 with Vite needs an explicit worker URL. MapLibre's CSS overrides Tailwind's `absolute`, so the map element sits inside a wrapper.

## Team and tasks

### Murat — backend, Java, Spring Boot, SQL, Docker, tests

1. Set up the monorepo, `.gitignore`, `.env.example`, and Docker Compose for local PostgreSQL, PostGIS, and pgvector.
2. Set up Aiven PostgreSQL Free and enable `postgis` and `vector`. Application tables are `places`, `photos`, `routes`, and `route_places`.
3. Implement `/api/places` with PostGIS bbox and tag filters, and `/api/routes` with ORS `foot-hiking`, waypoints, and persistence.
4. Import Tatras points of interest from Overpass using a one-time script.
5. Find photos along routes using `ST_DWithin(photo.geom, route.geom, 300m)` and group them into route segments.
6. Produce Kafka event `photo.uploaded` and cache ORS responses in Valkey.
7. Test PostGIS queries and deploy the API.

### Mukhamed — AI agent, Python, LLM, RAG

1. Build FastAPI `/api/chat` with sessions in Valkey.
2. Extract intent from free text as `{start, end, mustSee[], preferences[]}` using Claude tool use or structured output.
3. Use Exa to find places from descriptions such as “the waterfall from TikTok near Štrbské Pleso”, and search for photos and trail descriptions. **Always retain sourceUrl.**
4. Geocode results with Nominatim/OSM into `Place`.
5. Embed places and photo captions with Gemini, store them in pgvector, and rank results by user preferences.
6. Consume `photo.uploaded`, extract EXIF location, generate embeddings, and associate photos with nearby trails.
7. Cache Exa results in Valkey. Attend the Exa workshop on Saturday at 16:30, Loft fourth floor.

### Daniil — frontend, product, and pitch, React and Tailwind

1. Set up Vite, React, Tailwind, MapLibre, and OpenFreeMap.
2. Build the map and side panel with chat and manual place creation.
3. Render GeoJSON routes and place markers. Show photos and sources when selected.
4. Build a horizontal “What you will see along the way” gallery by route segment, synchronized with the map.
5. Support user photo uploads.
6. Use contract-based mocks while the backend services are being built.
7. Deploy the frontend, record the two-minute video, prepare the pitch deck PDF, and write the final submission.

## Timeline

| Time | Goal |
|---|---|
| Friday/Saturday, 00:00–03:00 | Obtain Exa, Claude, Gemini, and Aiven credits. Create the repository, provision Aiven services, scaffold the three services, and prepare mocks |
| Saturday, 03:00–09:00 | Rotate sleep shifts, at least four to five hours per person |
| **Saturday, 12:00** | **End-to-end MVP**, chat → places → route on the map, photos may follow |
| Saturday, 12:00–20:00 | Photos along routes, uploads, Kafka, caching, manual place creation |
| Saturday, 16:30 | Exa workshop for Mukhamed, others if possible |
| Saturday, 20:00–02:00 | Public deployment, demo polish, stretch work if time allows |
| Sunday, 02:00–07:00 | **Feature freeze**, video at most 2:00, deck PDF, description, README |
| **Sunday, 09:30** | **Submit Final**, deadline 10:00 |
| Sunday, 10:30 | Peer review, all team members present |

## Claude Code tools

MCP `context7` for library documentation is connected. Add Exa MCP and Aiven MCP, following https://aiven.io/docs/tools/mcp-server.

```sh
claude mcp add --transport http exa https://mcp.exa.ai/mcp
```

Role-specific skills listed in the original team plan follow.

- Murat — `ecc:springboot-patterns`, `ecc:springboot-tdd`, `ecc:postgres-patterns`, `ecc:docker-patterns`, `ecc:java-reviewer` agent.
- Mukhamed — `ecc:fastapi-patterns`, `ecc:exa-search`, `claude-api`, `ecc:rag-pipeline-reviewer` agent, `ecc:redis-patterns`, compatible with Valkey.
- Daniil — `ecc:react-patterns`, `impeccable` or `ecc:frontend-design-direction`, frontend slides or `anthropic-skills:pptx`, video work through `ecc:remotion-video-creation`.
- Everyone — `ecc:api-design`, `code-review`, and a final `ecc:security-review` for committed credentials.

## Decision log

- November 13 — Main challenge is Exa Internet Butler, technical challenge is Aiven. The product delegates live web research and presents sources.
- November 13 — Use partner credits and free tiers for the project budget.
- November 13 — Use the High Tatras for deeper demo testing while accepting other regions from live judge requests.
- November 13 — Use Spring Boot for data and geospatial operations, and FastAPI for the agent. Share PostgreSQL and Kafka. The frontend calls both services.
- November 14 — Local development and CI use PostgreSQL 18 with PostGIS and pgvector. Configure the port through POSTGRES_PORT. Docker init enables extensions, Flyway in api manages tables. CI runs on PR changes under infra/**. Verified locally and in GitHub Actions, PR #1.
- November 14 — English is the project language for repository files, commits, PRs, and reviews. Use descriptive task prefixes for new branches, such as feat/, fix/, docs/, infra/, or chore/.
- November 14 — Frontend stack is React, Vite, Tailwind and MapLibre with OpenFreeMap. Wikimedia Commons is the demo and fallback photo source.
- November 14 — Work is submitted as small PRs, stacked when large. Generated files are excluded from the size budget and stay in the same PR as their manifest.
- November 14 — Every PR requires review and approval by at least one developer other than the author, including internal changes that affect no other component. Request review from owners of the components affected by a PR. GitHub requires one independent approval. Additional reviewers are selected when their components or shared contracts are affected. Murat's assistant reviews backend, shared infrastructure, repository governance, and backend-facing integration. In a stack, retarget the next PR to main before merging it (#14 and #15 landed in stack branches and were re-landed in #21).
- November 14 — The hiking-intent adapter uses Claude tool use with a validated `{start, end, mustSee[], preferences[]}` result and at most six recent session exchanges. Blank values are normalized; results exceeding five intermediate stops or twelve preferences require user clarification. Provider requests have explicit timeouts and no automatic paid retries. The HTTP chat contract stays on the baseline; connecting intent and place discovery is a later block.
- November 14 — The internal Exa text-research adapter retains source URLs and caches responses in Valkey for 24 hours. [The agent delivery plan](docs/AGENT_PLAN.md) records sequential blocks and unresolved integration gates; shared API/schema/event proposals remain unapproved until the affected owners agree.
- November 14 — Internal place discovery combines intent, source-grounded resolution, and cached, rate-limited Nominatim lookup. The merged place API returns UUID strings; discovery findings retain research and OSM identity separately. The HTTP chat contract stays unchanged, and API write/route handoff remains pending owner agreement. Daniil confirmed in PR #28 that chat and clarification replies follow the user's message language, while UI labels remain English.

- November 14 — Murat selected Spring Data JPA for ordinary API persistence, with Hibernate Spatial for PostGIS mapping. Native JPA queries preserve the current spatial filters; JDBC remains an option for complex queries. Flyway continues to own schema changes, and application services own transaction boundaries. The implementation and shared documentation changes require the normal PR review.

## Open questions and completed checks

- [x] Aiven PostgreSQL Free supports PostGIS and pgvector. Verified with SQL on service junction on November 14, PostgreSQL 18.7, postgis 3.6.4, vector 0.8.7. Both extensions are enabled and the spatial and vector queries passed.
- [ ] Check Aiven Runtime credit pricing and select API and agent hosting.
- [ ] Display photo authors and source links. For TikTok links or descriptions supplied by users, use Exa to find relevant sources.
