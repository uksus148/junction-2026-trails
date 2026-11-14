# Places API

Use JDK 21 or newer, Maven 3.6.3+ and Docker Compose. The project targets Java 21 with Spring Boot 3.5.16, and CI runs on Java 21. Flyway 11.14.1 is pinned for PostgreSQL 18 support. Run application commands from `api/`; Spring reads the shared root `.env` as a properties file. Environment variables override values from that file.

## Code map

The API is one Spring Boot application organized by feature. Start with the feature you are reviewing, then follow its HTTP handler to the model and database query.

```text
api/
├── pom.xml
├── src/main/java/io/junction/trails/
│   ├── TrailsApplication.java
│   ├── config/
│   │   └── ApiWebConfiguration.java
│   └── places/
│       ├── web/
│       │   └── PlaceController.java
│       ├── model/
│       │   ├── BoundingBox.java
│       │   └── Place.java
│       └── persistence/
│           └── PlaceRepository.java
├── src/main/resources/
│   ├── application.properties
│   └── db/migration/
│       └── V1__create_places.sql
└── src/test/java/io/junction/trails/places/web/
    ├── PlaceSearchTest.java
    └── PlaceCorsConfigurationTest.java
```

| Package or directory | Responsibility |
|---|---|
| `config` | Shared Spring MVC settings, including allowed browser origins |
| `places/web` | HTTP parameters, response handling, and HTTP errors |
| `places/model` | Place data and bounding-box validation, independent of Spring and JDBC |
| `places/persistence` | Parameterized SQL and mapping database rows to models |
| `resources/db/migration` | Ordered Flyway migrations for the application's database schema |
| `test/java` | Tests that mirror production packages; the web test covers HTTP through PostGIS |

The dependency direction is `web → persistence → model`, with `web` also using the model directly. Future route and photo features belong in sibling `routes` and `photos` packages. Feature-specific business workflows can live in an `application` subpackage as they are implemented. This keeps route construction, caching, and upload processing close to their owning feature. Spring discovers components below `io.junction.trails`.

## Start locally

From the repository root, copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`. Change `POSTGRES_PORT` if 5432 is occupied.

```sh
docker compose --env-file .env -f infra/compose.yaml up --build --wait
cd api
mvn spring-boot:run
```

Flyway creates the `places` table on first startup. PostGIS and pgvector are enabled by the existing database initialization script. The table starts empty.

Browser requests to `/api/**` allow `http://localhost:5173` by default. Configure
`API_CORS_ALLOWED_ORIGINS` in the root `.env` or process environment as a
comma-separated list of exact frontend origins, without quotes. For example,
if Vite falls back to port 5174 or the frontend is deployed:

```dotenv
API_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,https://trails.example.org
```

Restart the API after changing origins. CORS permits GET and POST with the
`Content-Type` header, including browser preflight requests. Other origins and
methods are rejected. This configures browser access; it does not implement the
planned POST endpoints or enable credentialed cross-origin requests.

```sh
curl 'http://localhost:8080/api/places?bbox=20,49,21,50&tags=waterfall'
```

## Search decisions for review

- `bbox` is required and uses `minLon,minLat,maxLon,maxLat` in WGS84 degrees. Bounds must be finite, within longitude ±180 and latitude ±90, and strictly increasing. Split searches crossing the antimeridian into two bounding boxes.
- Points on the bounding box boundary are included. An omitted or blank `tags` parameter returns all matching places. Comma-separated tags match **any** requested tag, case-sensitively. Surrounding whitespace is trimmed; empty list entries produce HTTP 400.
- Results are ordered by ID. Place IDs are UUID strings. The response follows the `Place` contract, with `photos: []` until photo storage is implemented.
- Invalid parameters produce HTTP 400 with an English Problem Detail `detail` field.

## Verify

```sh
cd api
mvn verify
```

Tests build the existing `infra/postgres` image and start an isolated PostgreSQL 18 container. Flyway applies the migration, and HTTP tests verify filters, boundaries, coordinates, response fields and invalid parameters. Browser-access tests cover GET/POST preflight, successful and invalid search responses, denied origins/methods, and configurable frontend origins. Docker must be running. Tests use disposable credentials and a separate database.

The API workflow runs these checks for API, database image, or workflow changes. The workflow can be exercised on GitHub after this local work has been reviewed and published.

## Review order

1. [PlaceController](src/main/java/io/junction/trails/places/web/PlaceController.java) maps the GET request to the search operation.
2. [BoundingBox](src/main/java/io/junction/trails/places/model/BoundingBox.java) validates coordinates; [Place](src/main/java/io/junction/trails/places/model/Place.java) defines returned data.
3. [PlaceRepository](src/main/java/io/junction/trails/places/persistence/PlaceRepository.java) executes the spatial and tag filters.
4. [V1 migration](src/main/resources/db/migration/V1__create_places.sql) defines the table and indexes.
5. [PlaceSearchTest](src/test/java/io/junction/trails/places/web/PlaceSearchTest.java) verifies the complete HTTP-to-PostGIS path.

Maven generates compiled classes, reports, and the application JAR under `target/`. Source changes belong under `src/`.
