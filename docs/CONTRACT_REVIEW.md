# Contract review across frontend, api, and agent

Murat's local [CLAUDE.md](../CLAUDE.md), translated into English, provides the shared baseline. This file gathers decisions for discussion in the PR. Record agreed changes in the API contract section and decision log of CLAUDE.md.

## Initial flow

Chat returns places and an optional routeId. The API stores places and builds and saves a hiking route. The frontend displays GeoJSON, markers, and photos with sources. CLAUDE.md describes the required demo request.

| Component | Initial contract | Implementation owner |
|---|---|---|
| Chat | POST /api/chat returns reply, places, routeId? | Mukhamed |
| Places | GET /api/places with bbox and tags, POST /api/places | Murat |
| Routes | POST /api/routes, GET /api/routes/{id} | Murat |
| Photos | POST /api/photos publishes photo.uploaded | Murat and Mukhamed |
| Display | Place, Photo, and Route from CLAUDE.md | Daniil |

The backend starts from these endpoints and structures. Bbox order is minLon,minLat,maxLon,maxLat. Fields lat and lon use WGS84 degrees. GeoJSON coordinate order is longitude, latitude. Fields distanceKm, ascentM, and durationMin define distance, ascent, and time units.

## Proposal for the first end-to-end MVP

Connect the original chat, places, and route flow to live services first. Discuss day planning, personalization, and the new /api/itineraries endpoints from PR #3 and #5 as a contract extension. New TypeScript types need an agreed API and agent implementation plan.

| Decision | Participants | Required outcome |
|---|---|---|
| First demo scope | All three developers | Day-planning features included in the next demo and their implementation owners |
| Chat changes | Mukhamed and Daniil | Required mode, preferences, and preferencesPatch fields and compatibility with the initial response |
| Day planner | Murat and Daniil | Execution location of the algorithm and new endpoints needed after the route MVP |
| Transit legs | All three developers | Calculation and explanation of transit times if included in the demo |

Before implementing the relevant HTTP handlers, the backend will propose identifier types, success and error status codes, and the photo upload response in a dedicated PR. Review those details with the frontend and agent.

## Recording agreement

Daniil and Mukhamed respond in the PR containing this document or propose a CLAUDE.md edit. Include affected fields, an implementation owner, and an example request or response. Move the agreement into CLAUDE.md, update types and mocks, and verify an end-to-end request. Reconcile differences in PR #3 against Murat's published baseline.
