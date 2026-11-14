FROM postgres:18-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-${PG_MAJOR}-postgis-3 \
        postgresql-${PG_MAJOR}-postgis-3-scripts \
        postgresql-${PG_MAJOR}-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY init-extensions.sql /docker-entrypoint-initdb.d/10-extensions.sql
