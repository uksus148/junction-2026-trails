# API container

Build and run the Spring Boot API independently of the host JDK/Maven. This packages
the existing API; public hosting, ingress/TLS and registry publication remain separate
deployment decisions. Follow the [integration runbook](../docs/INTEGRATION_RUNBOOK.md)
for shared data targets and browser acceptance.

## Build

From the repository root:

```sh
docker build --tag trego-api:local api
```

The build context is only `api/`, with an allowlist in `.dockerignore`. The root `.env`,
private handoff files, existing JARs and test outputs are excluded. Maven/Java 21 builds
the executable JAR; the final stage contains the JAR and Temurin Java 21 JRE. Both base
images use multi-platform manifest digests. Update the tag and digest together when
adopting security updates, then rebuild and verify. Dependencies still follow `pom.xml`;
pinning base images is not a guarantee of fully reproducible Maven dependency resolution.

The container build skips tests because ordinary image builders have no Docker daemon
for Testcontainers. The API workflow runs `mvn verify` before building this image. Run
that check locally before publishing an image too. The Maven cache mount speeds rebuilds
and is not copied into the runtime stage.

## Run with Aiven

Copy `api/container.env.example` to the ignored root `.env.api-container`; fill its API-only
values privately. Keep values literal and unquoted: `docker --env-file` does not expand
`${...}`. The normal shared root `.env` remains for host-launched services. No new dotenv
loader is introduced. Configure the cloud port/database explicitly, retaining PostgreSQL
`verify-full` and the Valkey `rediss://` scheme.

Place the downloaded public Aiven PostgreSQL CA at `.env.certs/aiven-ca.pem` locally.
The file must be readable by container UID 10001; mode 0644 is appropriate for this public
CA certificate. Credentials stay in the private environment file (mode 0600). From the
repository root, with both files prepared:

```sh
docker run --rm --name trego-api \
  --publish 127.0.0.1:8080:8080 \
  --env-file .env.api-container \
  --mount "type=bind,src=$PWD/.env.certs/aiven-ca.pem,dst=/run/certs/aiven-ca.pem,readonly" \
  trego-api:local
```

The certificate path in JDBC is the container path `/run/certs/aiven-ca.pem`, not a path
on Murat's laptop. Use a free host port (for example `127.0.0.1:8081:8080`) if 8080 is
occupied and update the agent/frontend API URLs accordingly. For local Docker databases,
use a shared Docker network with service DNS names, or the appropriate host gateway;
`localhost` inside this container refers to the container itself.

Flyway applies migrations to the selected database at startup and Hibernate validates
them. Select the team's agreed integration target before starting; this is a real API
process and successful writes persist. Test outages only against isolated resources.

The Java process runs as UID/GID 10001 and receives Docker stop signals directly.
The JAR is owned by root with mode 0644; UID 10001 can read it but cannot replace
or modify it in the root-owned `/app` directory.
The image includes no provider keys, database credentials or certificates. The existing
application uses injected environment variables when no optional root `.env` is present.
Runtime configuration and logs should be kept private.

For a frontend deployed on Pages/Vercel, add its exact `https://...` origin to
`API_CORS_ALLOWED_ORIGINS` as an unquoted comma-separated value and configure the
frontend to use a reachable HTTPS API URL. When using separate laptops, publish
the API on the chosen LAN interface instead of `127.0.0.1` and allow the frontend's
exact LAN origin, including its port. Update both frontend and agent API URLs;
each laptop's `localhost` refers to itself. The default command is for one workstation.

## Check and stop

```sh
curl --fail 'http://localhost:8080/api/places?bbox=20,49,21,50'
docker stop trego-api
```

A successful search checks API/database availability. It does not check Valkey, ORS,
live chat or the browser; use the runbook's separate routing/cache and E2E checks.
Building an image or starting this container does not establish public deployment.

## Local verification

On November 14, 2026, the image built on Linux arm64 with Java 21 and ran as UID/GID
10001. An isolated smoke passed Flyway V1-V3, Hibernate validation, a readable read-only
CA mount, manual 201 creation, sourced 201/200 replay, CORS, route 201/GET 200 and a
cached repeat with one fixture ORS call and a bounded 24-hour TTL. Docker stop completed
without an OOM. Only its disposable containers/network were removed; the existing local
services and Aiven data were not changed. The generated local report is
`api/target/container-smoke.json` (ignored). This is container verification, not a new
live Aiven check or browser E2E result. The API workflow adds image construction after
Java 21 tests; see the PR for its actual CI result. This local smoke verifies arm64
runtime only; an amd64 image build alone does not establish amd64 runtime acceptance.

The PR #46 review follow-up rebuilt the arm64 image after rebasing onto merged #47.
The isolated smoke passed again and additionally verified `/app/app.jar` ownership
`0:0`, mode `0644`, and no write access to either the JAR or `/app` for UID 10001.
Its ignored report is `api/target/container-review-smoke.json`; application source
and dependencies match the rebased main. No live services were used for this check.

For size comparisons, record the architecture, image ID, Docker version and measurement.
`docker image ls` on the review workstation reports about 515 MB for the arm64 image;
the earlier author report recorded `docker image inspect`'s `Size` field near 155 MB.
These are different Docker measurements, not an established compressed registry size.
No registry image has been published; do not label the smaller figure as download size.
