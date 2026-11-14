# trego.

Plan a hiking route through interesting places and see photos along the way, with authors and source links. Describe your preferences in chat or choose places on a map.

The required demo route runs through the High Tatras, from Štrbské Pleso to Rysy via the Skok waterfall. Support for other regions depends on the readiness of the integrations.

## Team and repository layout

| Directory | Purpose and stack | Owner |
|---|---|---|
| frontend/ | Map, chat, places, and photos · React, Vite, Tailwind, MapLibre | Daniil · nnatthebest |
| api/ | Data, geospatial queries, routes, and uploads · Java, Spring Boot | Murat · uksus148 |
| agent/ | Chat, Exa search, photo processing, and embeddings · Python, FastAPI | Mukhamed · dyksookelwe |
| infra/ | Local database and environment checks · Docker Compose | Murat |

Planned shared services are Aiven PostgreSQL with PostGIS and pgvector, Valkey, and Kafka. The API uses OpenRouteService for hiking routes. The agent searches through Exa and retains source links.

## Getting started

1. Clone the repository and create a task branch from the current main. Use a descriptive prefix such as feat/, fix/, docs/, infra/, or chore/.
2. Read [CLAUDE.md](CLAUDE.md) for architecture, the API contract, and team tasks.
3. Copy `.env.example` to a root `.env` and fill in values for your service. The template lists shared addresses and empty secret fields.
4. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [repository rules](docs/REPOSITORY_RULES.md) before opening a PR.

```sh
git clone https://github.com/uksus148/trego.git
cd trego
cp .env.example .env
```

The local database requires Docker and Docker Compose. PostgreSQL 18, PostGIS, pgvector, and a configurable port are prepared in [PR #1](https://github.com/uksus148/trego/pull/1), which includes setup instructions and CI results. The frontend is under review in [PRs #4–10](https://github.com/uksus148/trego/pulls). Each service adds its run commands to its own directory as implementation progresses.

Aiven Free has been verified with PostgreSQL 18.7, PostGIS 3.6.4, and pgvector 0.8.7. Share service credentials through a private channel. Git ignores the local `.env`.

For backend development, start with the [API code map, run commands, and review order](api/README.md).

## Shared contract and project language

The API contract section in [CLAUDE.md](CLAUDE.md) defines the baseline. Day-planning and personalization proposals are listed in the [contract review](docs/CONTRACT_REVIEW.md). Affected developers discuss changes and record the agreement in CLAUDE.md.

English is the project language for repository files, code comments, documentation, commits, PRs, and reviews.

## License

The project code is distributed under [MIT](LICENSE).
