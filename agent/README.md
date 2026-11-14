# GOPSTOP.PROTOCOL Agent

The agent is a FastAPI service implementing the baseline `POST /api/chat` contract.
It stores exchanges in Valkey and can discover sourced places with Claude, Exa,
and Nominatim. Discovery is opt-in to conserve credits during local development.

## Run locally

From this directory, create and activate a virtual environment, then install the service and test dependencies:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

For reproducible installs with uv, run `uv sync --frozen --extra test` instead;
`uv.lock` is committed alongside `pyproject.toml`.

Settings load from the repository root `.env` and process environment. Set `AGENT_VALKEY_URL` to a Redis-compatible Valkey URL; when it is unset, the service also accepts the shared `SPRING_DATA_REDIS_URL` variable. The default is `redis://localhost:6379/0`. `AGENT_SESSION_TTL_SECONDS` defaults to 86400 (one day), and `AGENT_SESSION_MAX_MESSAGES` defaults to 200 messages per session (must be even so history is retained in complete user/assistant exchanges). Start the API with:

```sh
uvicorn gopstop_agent.main:app --reload
```

Browser calls are allowed from `http://localhost:5173` by default. Set
`AGENT_CORS_ORIGINS` to a JSON list of frontend origins for deployment, for example
`["https://trails.example.org"]`. Only POST and the Content-Type request header are
allowed. Valkey connection and read/write timeouts default to two seconds each;
configure `AGENT_VALKEY_CONNECT_TIMEOUT_SECONDS` and
`AGENT_VALKEY_SOCKET_TIMEOUT_SECONDS` to change them. Timeouts return the same 503
as connection failures. These settings are listed in the root `.env.example`.

## Chat contract

```http
POST /api/chat
Content-Type: application/json

{"sessionId":"demo-session","message":"I want to hike from Štrbské Pleso to Rysy via Skok waterfall."}
```

The response follows `{reply, places:[Place], routeId?}`. `routeId` is omitted
because route persistence is not connected yet. Invalid payloads return 422;
storage/provider failures return 503 without saving a successful exchange.

Run automated tests with `pytest`.

## Intent extraction

`ClaudeIntentExtractor` uses Claude tool use and validates the internal
`{start, end, mustSee[], preferences[]}` result. It accepts recent session history,
keeps unknown endpoints null, and never asks the model for coordinates. The
adapter uses recent session history for follow-ups. There are no live provider
calls in the test suite.

Set `ANTHROPIC_API_KEY` in the root `.env`. `AGENT_ANTHROPIC_MODEL` follows the
team-plan default `claude-haiku-5-5`; select a model available to the team's account
before live testing. `AGENT_PROVIDER_TIMEOUT_SECONDS` defaults to 20. No automatic
paid retries are performed. Live account/model availability has not been verified.

## Place research providers

`ExaSearch` searches live web text and always preserves each result's URL.
Valkey caches query hashes for 24 hours. `NominatimGeocoder` resolves descriptive
names into WGS84 coordinates with stable OSM identifiers, caches responses for
24 hours, and uses a shared Valkey gate to limit requests to one per second.
Missing or ambiguous coordinates stay unresolved. Set `EXA_API_KEY` in the root
`.env` and configure `AGENT_NOMINATIM_USER_AGENT` with the team's contact identity.
`AGENT_NOMINATIM_BASE_URL` permits switching to a hosted geocoder. Display
OpenStreetMap attribution when using its coordinates. Photo URLs and licensing
are not inferred from arbitrary web images. Tests use fixtures and make no live requests.

## Enable place discovery

Set `AGENT_ENABLE_DISCOVERY=true` with `ANTHROPIC_API_KEY`, `EXA_API_KEY`, and a
working Valkey connection in the root `.env`. Choose an available Claude model
using `AGENT_ANTHROPIC_MODEL`. Send the Tatras example above, then a follow-up.
Chat returns uniquely geocoded places, source links, and OSM attribution. Missing
or ambiguous places trigger a clarification. `AGENT_CHAT_TIMEOUT_SECONDS` bounds
the entire request (default 60 seconds), including provider calls and storage.
When discovery is disabled, chat saves the message and returns a placeholder.

Discovered IDs use `osm:<type>:<id>` and are not yet persisted API place IDs.
Do not pass them to `/api/routes` until the API ingestion/identifier agreement is
implemented. Route creation, licensed photo discovery, Gemini/pgvector ranking,
and Kafka EXIF ingestion remain follow-up work. SQL tables and migrations belong
to `api`; no guessed schema or event payload is introduced here.
