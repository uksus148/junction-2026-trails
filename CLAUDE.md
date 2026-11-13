# GOPSTOP.PROTOCOL — Junction 2026

AI route planner: the user tells the chat (or marks on the map) what they want to see — castles, waterfalls, views —
and gets a hiking route from A to B through those places, with real photos of the views along the way and a source for each one.

This file is the single source of truth for the team and for AI assistants. Update it with every decision.

## Challenges
- **Main:** The Internet Butler / Your Personal Assistant — **Exa**. Judged on: using Exa for information a model can't know from training data;
  usefulness to a specific group (hikers, travellers); visible sources; originality; the demo must work on **live queries from the judges**.
- **Tech:** Best Use of **Aiven**. Meaningful use 40% / technical implementation 30% / impact on the solution 20% / creativity 10%.
- Optional: Cloudinary (separate form: https://cld.media/hackathon-survey) if user photo uploads go through it.

## Junction rules that matter
- All code is written during the event (hacking started Fri 13.11 19:30). The repository is **public**, licence **MIT**.
- **Final submission: Sun 15.11 10:00** — switch the project from Draft to Final. Late submissions are not accepted.
- Video pitch **2:00 max**, public link (YouTube/Vimeo). Pitch deck as PDF.
- **Sun 10:30–13:00 peer review — all three of us on site**, otherwise we are not eligible for the main prize.
- Top 5: 3 min pitch + 3 min questions.

## Working agreements
- **Everything on GitHub is in English:** code, comments, commit messages, PR titles and descriptions, review comments, docs in the repo.
- Follow `CONTRIBUTING.md`: one branch per task, Conventional Commits `type(scope): …`, squash merge after one Approve.
- **Small PRs.** Aim for under ~400 hand-written lines per PR; split bigger work into a stack of PRs that each build and pass tests.
  Generated files (lockfiles) go in their own PR so reviewers can skip them.
- One `.env` at the repo root for every service; the template is `/.env.example`. Secrets never go into git.

## Budget: we buy nothing
| Need | Use | Cost to us |
|---|---|---|
| Web search for places and photos | **Exa** $50 × 3 = $150 | partner credits |
| Agent LLM | **Claude API** $20 × 3 (`claude-haiku-5-5` by default, `claude-sonnet-5-5` only for planning) | partner credits |
| Embeddings | **Gemini API** | partner credits / free tier |
| Coding help | Codex $100 | partner credits |
| Database | **Aiven PostgreSQL** free plan (check pgvector + PostGIS in the console) | free |
| Cache | **Aiven Valkey** free plan | free |
| Event queue | **Aiven Kafka** — paid from the $50 Aiven credits, smallest plan, power off when idle | credits |
| Observability (stretch) | Aiven ClickHouse — only if credits remain | credits |
| Map | MapLibre GL + OpenFreeMap tiles (no key) | free |
| Points of interest | OSM Overpass API (`historic=castle`, `waterway=waterfall`, `tourism=viewpoint`, `natural=peak`) | free |
| Hiking routing | OpenRouteService `foot-hiking` (free key, ~2000 requests/day) | free |
| Photos | Wikimedia Commons API, Mapillary (free token), Exa; user uploads via Cloudinary free tier | free |
| API/agent hosting | Aiven Runtime if credits allow, otherwise Modal ($100 credits) | credits |
| Frontend hosting | Cloudflare Pages / Vercel free tier | free |

**Not used:** Oxylabs (needs a credit card and a subscription), paid video-generation tools, GPU clouds (not needed).
**Saving credits:** cache every Exa and routing response in Valkey (key = request hash, TTL 24 h). Use recorded fixtures during development, not live calls.

## Architecture
```
frontend (React + Vite + Tailwind + MapLibre)
   │ REST
   ├──► api (Spring Boot, Java)     — places, routes, itineraries, uploads, PostGIS queries, ORS routing
   │       │ Kafka: photo.uploaded, route.requested
   └──► agent (FastAPI, Python)     — chat, LLM intent extraction, Exa search, embeddings, photo pipeline
           │
   Aiven PostgreSQL (PostGIS + pgvector) · Aiven Valkey (cache, chat sessions) · Aiven Kafka
```

### Demo scenarios (must work flawlessly)
- **Route:** High Tatras — "I want to hike from Štrbské Pleso up to Rysy and see the Skok waterfall on the way. I love wild views."
  → the agent finds Skok and Rysy → a route through them → track, points and photos of every segment with sources.
- **Day plan:** Bratislava — "Plan my day in Bratislava from 10:00, no museums please, I hate crowds" → timed schedule, then Skip / Done / Running late.
- A judge will type their own query, so nothing is hard-coded to one region.

### API contract (change only by agreement; record every change here)
- `POST /api/chat` `{sessionId, message, mode: 'route'|'day', preferences}` → `{reply, places: [Place], mode, routeId?, itineraryId?, preferencesPatch?}` (agent).
  The agent decides `mode` (an explicit request for a day plan → `day`) and returns preferences it understood from the text in `preferencesPatch`.
- `GET /api/places?bbox=minLon,minLat,maxLon,maxLat&tags=castle,waterfall` → `[Place]` (api)
- `POST /api/places` `{name, lat, lon, tags[]}` → `Place` — manual add (api)
- `POST /api/routes` `{start: {lat, lon}, end: {lat, lon}, placeIds[], preferences[]}` → `Route` (api)
- `GET /api/routes/{id}` → `Route`
- `POST /api/itineraries` `{start, placeIds[], preferences, startTime, endTime}` → `Itinerary` (api)
- `GET /api/itineraries/{id}` → `Itinerary`
- `POST /api/itineraries/{id}/replan` `{now, location?, skipPlaceIds[], donePlaceIds[], preferences?}` → `Itinerary`
- `POST /api/photos` multipart `{file, lat, lon}` → publishes `photo.uploaded` to Kafka

Shapes (source of truth in code: `frontend/src/types.ts`):
- `Place = {id, name, lat, lon, tags[], photos: [Photo], source, dwellMin?, priceLevel? (0-3), crowdLevel? (0-2), openingHours? {open, close: 'HH:MM'}}`
- `Photo = {url, thumbUrl, author, license, sourceUrl, lat, lon}`
- `Route = {id, geojson (LineString), distanceKm, ascentM, durationMin, places: [Place], segments: [{fromKm, toKm, photos: [Photo]}]}`
- `Preferences = {interests[], dislikes[], pace: 'relaxed'|'normal'|'intense', maxWalkKm, budget: 0-3, avoidCrowds}`
- `Itinerary = {id, route, start, startTime, endTime, resumeAt, candidates: [Place], preferences, stops: [ItineraryStop], dropped: [{place, reason}], walkKm}`
- `ItineraryStop = {place, arriveAt, leaveAt, travelMin, travelKm, travelMode: 'walk'|'transit', status: 'planned'|'done'|'skipped'}`
- `reason ∈ dislike | budget | closed | no_time | walk_limit | skipped_by_user`

**Reference algorithm:** `frontend/src/lib/planner.ts` — greedy selection → 2-opt reordering → fill freed time; replanning runs the same
scheduler from `now` over the remaining places. Port it 1:1 to Java (api); its behaviour is pinned by `frontend/src/lib/planner.test.ts`,
repeat the same cases in JUnit. Intent parsing reference for the agent: `frontend/src/lib/intent.ts` + tests.

### Repository layout
```
/frontend   — Daniil
/api        — Murat
/agent      — Muhamed
/infra      — docker-compose for local dev, SQL migrations
```

### Frontend status
```
cd frontend && npm install && npm run dev   # http://localhost:5173
npm test                                    # vitest
```
- Map (MapLibre + OpenFreeMap), chat, manual planning (A/B + own places), route with highlighted segments,
  "What you'll see on the way" strip, photo viewer with author, licence and source.
- **Day plan** switch, **Me** tab (interests, dislikes, pace, walking limit, budget, crowds; stored in localStorage),
  day timeline with **Done / Skip / Running late +15/30/60 / Replan from now** and a "Left out and why" list. Day demo: Bratislava.
- Runs on **in-browser mocks** by default (`VITE_USE_MOCKS=true`): Tatras route and Bratislava day demo, straight lines between points,
  **live photos from Wikimedia Commons** (free, no key). Real backends: set `VITE_USE_MOCKS=false`, `VITE_API_BASE_URL`, `VITE_AGENT_BASE_URL` in the root `.env`.
- Gotchas: with MapLibre v6 + Vite the worker URL is set explicitly (`setWorkerUrl` in `MapView.tsx`); MapLibre's CSS overrides Tailwind's
  `absolute`, so the map element sits inside a wrapper.

## Team and tasks

### Murat — backend (Java + Spring Boot, SQL, Docker, tests)
1. Monorepo, `.gitignore`, `.env.example`, `docker-compose` (local Postgres + PostGIS) — done
2. Aiven PostgreSQL (free plan) with `postgis` and `vector`. Schema: `places`, `photos`, `routes`, `route_places`, `itineraries`
3. `/api/places` (bbox + tags via PostGIS), `/api/routes` (ORS foot-hiking through waypoints, persisted)
4. One-off import of Tatras POIs from Overpass into `places`
5. Photos along a route: `ST_DWithin(photo.geom, route.geom, 300 m)` → split by segment
6. Kafka producer `photo.uploaded`; Valkey cache for ORS responses
7. `/api/itineraries` (create / get / replan) — port `frontend/src/lib/planner.ts`
8. Tests for PostGIS queries and the planner; deployment

### Muhamed — AI agent (Python, LLM, RAG)
1. FastAPI service `/api/chat`, chat sessions in Valkey
2. Intent extraction: free text → `{mode, start, end, mustSee[], preferencesPatch}` (LLM structured output; reference behaviour in `frontend/src/lib/intent.ts`)
3. Exa: find a place from a description ("the waterfall from TikTok near Štrbské Pleso"), photos and trail descriptions; **always keep `sourceUrl`**
4. Exa: fill `openingHours`, `priceLevel`, `crowdLevel`, `dwellMin` for places in day plans
5. Geocoding via Nominatim/OSM → `Place`
6. Embeddings (Gemini) for places and photo captions → pgvector; rank what the user will like
7. Kafka consumer `photo.uploaded`: EXIF geotag → embedding → attach to the nearest trail
8. Exa responses cached in Valkey. Exa workshop: Sat 16:30, Loft, 4th floor

### Daniil — frontend + product and pitch (React, Tailwind)
1. Frontend app on mocks following the contract above — done
2. Switch to real backends as they land
3. User photo upload
4. Deploy the frontend; 2-minute video, pitch deck PDF, final submission text

## Timeline
| When | Goal |
|---|---|
| Sat by ~03:00 | Credits claimed (Exa, Claude, Gemini, Aiven), repo created, Aiven services up, skeletons of all three services |
| Sat 03:00–09:00 | Sleep in shifts (at least 4–5 h each) |
| **Sat 12:00** | **End-to-end MVP:** chat → places → route on the map |
| Sat 12:00–20:00 | Photos along the route, uploads via Kafka, caching, day plans on real data |
| Sat 16:30 | Exa workshop |
| Sat 20:00–02:00 | Deploy to a public URL, polish the demo scenarios |
| **Sun 02:00** | **Feature freeze.** Only bug fixes, video, deck, README |
| **Sun 09:30** | **Submit Final** (deadline 10:00) |
| Sun 10:30 | Peer review — everyone on site |

## Dev tooling
- MCP servers worth adding: Exa (`claude mcp add --transport http exa https://mcp.exa.ai/mcp`) and Aiven (https://aiven.io/docs/tools/mcp-server).
- Before the final submission: run a code review and a security review (no keys in the repo).

## Decision log
- 13.11 — Main challenge: Exa Internet Butler; tech challenge: Aiven. The product is an agent doing tedious research on the live web, with sources.
- 13.11 — We buy nothing: partner credits and free tiers only (budget table above).
- 13.11 — Two backends matching the team's skills: Spring Boot (data, geo) + FastAPI (agent). They share the database and Kafka; the frontend calls both.
- 13.11 — One region for the route demo (High Tatras), nothing hard-coded so judges' queries work.
- 14.11 — Repository: https://github.com/uksus148/junction-2026-trails, rules in `CONTRIBUTING.md`. One `.env` at the root for all services.
- 14.11 — Frontend: React 19 + TypeScript + Vite 8 + Tailwind 4 + MapLibre 6. UI in English (international jury).
- 14.11 — Demo photos and the fallback photo source: Wikimedia Commons geosearch (free, CORS enabled, includes author and licence).
- 14.11 — Added deep personalisation and a "Day plan" mode with replanning. The mode is optional (a switch + detection in chat).
  One scheduler for planning and replanning; dropped places are shown with a reason (transparency for the Exa judges).
- 14.11 — A leg longer than 2.5 km is public transport (18 km/h + 8 min wait) and does not count towards the walking limit.
- 14.11 — Everything on GitHub in English; work goes in as a stack of small PRs (see Working agreements).

## Open questions
- [ ] Are pgvector and PostGIS available on the Aiven PostgreSQL free plan? If not, Hobbyist plan from credits.
- [ ] Aiven Runtime cost in credits → decide where the api and agent are hosted.
- [ ] Photo licences: only shown with author and link. TikTok is not scraped — the user pastes a link or description and we search with Exa.
- [ ] "Replan from now" uses the device time zone, not the destination's.
- [ ] The map re-fits to the whole day after every replan.
