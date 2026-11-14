# trego. Local infrastructure

PostgreSQL 18 with PostGIS and pgvector matches the major version selected by Aiven Free. Install Docker with Compose and choose a free local port.

From the repository root, copy `.env.example` to `.env` once and set `POSTGRES_PASSWORD`. If port 5432 is occupied, change `POSTGRES_PORT` in `.env`. The API running on the host uses the same port in `SPRING_DATASOURCE_URL`.

```sh
docker compose --env-file .env -f infra/compose.yaml up --build --wait
docker compose --env-file .env -f infra/compose.yaml exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < infra/smoke.sql
```

The smoke test checks a spatial query and a vector distance without changing the database. It fails if initialization omitted either extension or a calculation returns the wrong result. GitHub Actions runs the same SQL for PR changes under `infra/` or to `.github/workflows/infra.yml`.

```sh
docker compose --env-file .env -f infra/compose.yaml down
```

The named volume retains data between runs. On its first start with an empty volume, PostgreSQL enables `postgis` and `vector`. Flyway migrations in the `api/` module will create application tables as the API is developed.
