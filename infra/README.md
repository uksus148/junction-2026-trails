# trego. Local infrastructure

PostgreSQL 18 with PostGIS and pgvector matches the major version selected by Aiven Free.
Valkey supplies the local API routing cache and agent cache/sessions. The deployed cache
uses Aiven Valkey. Install Docker with Compose and choose free local ports.

From the repository root, copy `.env.example` to `.env` once and set `POSTGRES_PASSWORD`.
If port 5432 or 6379 is occupied, change `POSTGRES_PORT` or `VALKEY_PORT` in `.env` and use
that port in the host-side client URLs. Both ports bind only to localhost. The local Valkey
cache is disposable and has no persistence volume; PostgreSQL retains saved routes.

```sh
docker compose --env-file .env -f infra/compose.yaml up --build --wait
docker compose --env-file .env -f infra/compose.yaml exec -T valkey valkey-cli ping
docker compose --env-file .env -f infra/compose.yaml exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < infra/smoke.sql
```

The SQL smoke test checks a spatial query and a vector distance without changing the database.
It fails if initialization omitted either extension or a calculation returns the wrong result.
GitHub Actions runs the same SQL and verifies Valkey is reachable for PR changes under
`infra/` or to `.github/workflows/infra.yml`. API tests check cache TTL and failure behavior.
The API and tests use the same Valkey 8.1 image line; this does not assert the Aiven service's
engine version. Deploy using the team's Aiven TLS endpoint as described in [the route guide](../api/ROUTES.md#configure-aiven-valkey).

```sh
docker compose --env-file .env -f infra/compose.yaml down
```

The named volume retains data between runs. On its first start with an empty volume, PostgreSQL enables `postgis` and `vector`. Flyway migrations in the `api/` module will create application tables as the API is developed.
