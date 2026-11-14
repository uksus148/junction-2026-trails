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

## Chat contract

```http
POST /api/chat
Content-Type: application/json

{"sessionId":"demo-session","message":"I want to hike from Štrbské Pleso to Rysy via Skok waterfall."}
```

The response follows the shared contract: `{ "reply": string, "places": [] }`, with `routeId` omitted until a route is available. Invalid payloads return FastAPI's `422` validation response. If Valkey is unavailable, the service returns `503` and does not claim that the message was saved.

Run automated tests with `pytest`.
