# Places API

Use JDK 21 or newer, Maven 3.6.3+ and Docker Compose. The project targets Java 21 with Spring Boot 3.5.16, and CI runs on Java 21. Flyway 11.14.1 is pinned for PostgreSQL 18 support. Run application commands from `api/`; Spring reads the shared root `.env` as a properties file. Environment variables override values from that file.

## Code map

The API is one Spring Boot application organized by feature. Follow a request through its controller, application service, and JPA repository. Persistence entities are separate from the records returned over HTTP.

```text
api/
├── pom.xml
├── src/main/java/io/junction/trails/
│   ├── TrailsApplication.java
│   ├── config/
│   │   ├── ApiWebConfiguration.java
│   │   └── ApiCorsProperties.java
│   └── places/
│       ├── web/
│       │   ├── PlaceController.java
│       │   ├── CreatePlaceRequest.java
│       │   └── PlaceExceptionHandler.java
│       ├── application/
│       │   └── PlaceService.java
│       ├── model/
│       │   ├── BoundingBox.java
│       │   ├── NewPlace.java
│       │   ├── Place.java
│       │   └── InvalidPlaceInputException.java
│       └── persistence/
│           ├── PlaceRepository.java
│           └── PlaceEntity.java
├── src/main/resources/
│   ├── application.properties
│   └── db/migration/
│       └── V1__create_places.sql
└── src/test/java/io/junction/trails/places/
    ├── model/
    │   ├── BoundingBoxTest.java
    │   └── NewPlaceTest.java
    └── web/
        ├── PlaceApiTest.java
        └── PlaceCorsConfigurationTest.java
```

| Package or directory | Responsibility |
|---|---|
| `config` | Shared Spring MVC settings and immutable configuration properties, including allowed browser origins |
| `places/web` | HTTP parameters, response handling, and HTTP errors |
| `places/application` | Search and creation workflows, transaction boundaries, and entity-to-response mapping |
| `places/model` | Validated input values and response snapshots, independent of Spring and persistence |
| `places/persistence` | JPA entities, Spring Data repositories, and parameterized native spatial queries |
| `resources/db/migration` | Ordered Flyway migrations for the application's database schema |
| `test/java` | Tests that mirror production packages; the web test covers HTTP through PostGIS |

The request flow is `web → application → persistence`; each layer uses model values as needed. The service currently depends on the JPA repository and maps its entities to response records inside the transaction. Controllers never serialize entities. Future route and photo features belong in sibling `routes` and `photos` packages. Spring discovers components below `io.junction.trails`.

Components use Lombok `@RequiredArgsConstructor` with final dependency fields, without `@Autowired` on the single generated constructor. Maven configures the annotation processor explicitly, using the Lombok version managed by Spring Boot; Lombok is excluded from the executable JAR. `ApiWebConfiguration` receives the immutable `ApiCorsProperties` bean. Use Lombok for ordinary accessors and constructors in other Java classes too. `PlaceEntity` uses field-level `@Getter` and a protected `@NoArgsConstructor`; derived coordinates, defensive collection access, and validated initialization remain explicit. Add `@Setter` only for properties intended to support unrestricted assignment. Records already provide their component accessors.

Spring Data JPA handles ordinary persistence. Hibernate Spatial maps the JTS point to the existing PostGIS column, and Hibernate maps tags to PostgreSQL `text[]`. The spatial search stays an explicit native query, including array-overlap filtering. JDBC remains available through Spring's JDBC support for future complex queries that justify a dedicated adapter; no extra query framework is introduced in advance.

## Start locally

From the repository root, copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`. Change `POSTGRES_PORT` if 5432 is occupied.

```sh
docker compose --env-file .env -f infra/compose.yaml up --build --wait
cd api
mvn spring-boot:run
```

Flyway creates the `places` table on first startup. Hibernate validates the existing schema with `ddl-auto=validate`; it does not create or update tables. Open EntityManager in View is disabled. PostGIS and pgvector are enabled by the existing database initialization script. The table starts empty.

Browser requests to `/api/**` allow `http://localhost:5173` by default. Configure
`API_CORS_ALLOWED_ORIGINS` in the root `.env` or process environment as a
comma-separated list of exact frontend origins, without quotes. For example,
if Vite falls back to port 5174 or the frontend is deployed:

```dotenv
API_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,https://trails.example.org
```

Restart the API after changing origins. CORS permits GET and POST with the
`Content-Type` header, including browser preflight requests. Other origins and
methods are rejected. Credentialed cross-origin requests are not enabled.

```sh
curl 'http://localhost:8080/api/places?bbox=20,49,21,50&tags=waterfall'
```

## Search decisions for review

- `bbox` is required and uses `minLon,minLat,maxLon,maxLat` in WGS84 degrees. Bounds must be finite, within longitude ±180 and latitude ±90, and strictly increasing. Split searches crossing the antimeridian into two bounding boxes.
- Points on the bounding box boundary are included. An omitted or blank `tags` parameter returns all matching places. Comma-separated tags match **any** requested tag, case-sensitively. Surrounding whitespace is trimmed; empty list entries produce HTTP 400.
- Results are ordered by ID. Place IDs are UUID strings. The response follows the `Place` contract, with `photos: []` until photo storage is implemented.
- Invalid parameters produce HTTP 400 with an English Problem Detail `detail` field.

## Create a place

```sh
curl -i 'http://localhost:8080/api/places' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Skok waterfall","lat":49.1536,"lon":20.0417,"tags":["waterfall","nature"]}'
```

The implementation returns HTTP **201 Created** and a `Place` with a generated UUID, the supplied coordinates, `photos: []`, and server-assigned `source: "manual"`. This completes the frontend's existing `addPlace` operation. The frontend and agent owners confirmed these manual-write semantics in [PR #33](https://github.com/uksus148/junction-2026-trails/pull/33); they are recorded in the canonical [API contract](../CLAUDE.md#api-contract). Researched provenance, OSM deduplication, and route handoff remain subject to separate agreement.

Name, latitude, longitude, and tags are required. Name must contain non-whitespace characters; coordinates must be finite and within WGS84 ranges. Tags may be empty; each supplied entry must be non-null and non-blank. Names and tags are stripped of surrounding whitespace, and repeated tags are removed while preserving order and case. An input `source` field cannot override the server-assigned value. Invalid or malformed input returns HTTP 400 and does not insert a row. Recognized input errors have a dedicated exception mapping; unexpected failures remain server errors.

The creation transaction finishes before the response is returned. A subsequent matching bbox/tag search returns the created place. Creation does not perform name-based deduplication; separate requests create separate records. The read and write paths use the original Flyway schema, with no migration rewrite.

## Verify

```sh
cd api
mvn verify
```

Tests build the existing `infra/postgres` image and start an isolated PostgreSQL 18 container. Flyway applies the migration and Hibernate validates the entity mapping. HTTP tests verify search, creation followed by search, invalid-input rejection without writes, coordinate order and limits, tag-array mapping, and unexpected server errors. Model tests exercise constructor invariants and collection snapshots. Browser-access tests cover GET/POST preflight, successful and invalid search responses, denied origins/methods, and configurable frontend origins. Docker must be running. JDBC is used in integration tests to seed and independently inspect the database.

The API workflow runs these checks for API, database image, or workflow changes. The workflow can be exercised on GitHub after this local work has been reviewed and published.

## Review order

1. [PlaceController](src/main/java/io/junction/trails/places/web/PlaceController.java) handles GET and POST; [CreatePlaceRequest](src/main/java/io/junction/trails/places/web/CreatePlaceRequest.java) converts nullable JSON input into a validated command.
2. [NewPlace](src/main/java/io/junction/trails/places/model/NewPlace.java) and [BoundingBox](src/main/java/io/junction/trails/places/model/BoundingBox.java) enforce input invariants at construction. [Place](src/main/java/io/junction/trails/places/model/Place.java) defines the response snapshot.
3. [PlaceService](src/main/java/io/junction/trails/places/application/PlaceService.java) owns transactions, source assignment, and response mapping.
4. [PlaceEntity](src/main/java/io/junction/trails/places/persistence/PlaceEntity.java) maps the existing schema; [PlaceRepository](src/main/java/io/junction/trails/places/persistence/PlaceRepository.java) supplies JPA persistence and native spatial queries.
5. [PlaceExceptionHandler](src/main/java/io/junction/trails/places/web/PlaceExceptionHandler.java) maps known place-input failures to HTTP 400.
6. [V1 migration](src/main/resources/db/migration/V1__create_places.sql) remains the schema owner. [PlaceApiTest](src/test/java/io/junction/trails/places/web/PlaceApiTest.java) verifies the complete HTTP-to-PostGIS path.

Maven generates compiled classes, reports, and the application JAR under `target/`. Source changes belong under `src/`.
