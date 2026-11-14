# GOPSTOP.PROTOCOL Agent

The agent is a FastAPI service implementing the baseline `POST /api/chat` contract. This first block validates requests, stores each user/assistant exchange in Valkey, and returns an honest placeholder response with no discovered places until the intent and search integrations are implemented.

## Run locally

From this directory, create and activate a virtual environment, then install the service and test dependencies:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

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

If port 5173 is busy, Vite may start the frontend on 5174. Check the URL printed
by Vite and add that exact origin to `AGENT_CORS_ORIGINS` in the root `.env`, for
example `AGENT_CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]`.
Restart the agent after changing this setting so the browser preflight succeeds.

## Chat contract

```http
POST /api/chat
Content-Type: application/json

{"sessionId":"demo-session","message":"I want to hike from Štrbské Pleso to Rysy via Skok waterfall."}
```

The response follows the shared contract: `{ "reply": string, "places": [] }`, with `routeId` omitted until a route is available. Invalid payloads return FastAPI's `422` validation response. If Valkey is unavailable, the service returns `503` and does not claim that the message was saved.

Run automated tests with `pytest`.
