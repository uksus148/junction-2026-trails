# Groq integration test

Use one worker and one tester initially. Follow the accepted D1-D5 contract and
[runbook](../docs/INTEGRATION_RUNBOOK.md). E1/E2 merged in #45/#43; deploy reviewed
code and Flyway V3. This PR adds Groq; actual access remains a team-machine check.

## Configure the root environment

Preserve private values in ignored root `.env`; copy missing settings from `.env.example`:

```dotenv
AGENT_LLM_PROVIDER=groq
GROQ_API_KEY=
EXA_API_KEY=
AGENT_GROQ_MODEL=openai/gpt-oss-120b
AGENT_CHAT_ENABLED=false
AGENT_DISCOVERY_TIMEOUT_SECONDS=90
AGENT_CHAT_TIMEOUT_SECONDS=180
AGENT_NOMINATIM_USER_AGENT=trego/0.1 (contact: https://github.com/uksus148/trego./issues)
```

Fill the two empty keys privately. Groq mode needs no `ANTHROPIC_API_KEY`.
Set `ORS_API_KEY` and PostgreSQL/Valkey connection fields for Spring;
`AGENT_VALKEY_URL` must select the agent's actual store and `AGENT_API_BASE_URL` its API.
Keep TLS verification. All services load root `.env`; do not shell-source it.
The source default remains Anthropic for compatibility; explicitly select
`AGENT_LLM_PROVIDER=anthropic` and its key/model only when using that provider.

## Preflight, then enable chat

Start reviewed API code (`cd api`, then `mvn spring-boot:run`) and confirm V3.
From `agent/`, run:

```sh
uv sync --frozen --extra test
mkdir -p target
uv run --frozen python -m gopstop_agent.smoke > target/e4-agent.json
```

This explicitly makes three LLM tool calls, one live Exa search in a unique temporary
cache namespace, a Nominatim lookup (possibly cached), session write/read and read-only
API GET. It deletes only its own temporary keys. Old Exa cache hits cannot validate a
bad key. Exit 0 / `status: passed` confirms these checks, not V3 or browser acceptance.
Ambiguous geocoding is reported separately. Reports omit keys, messages and provider bodies.

After this PR is reviewed/merged, the API is migrated and E4 passes on the team's machine,
set `AGENT_CHAT_ENABLED=true` in root `.env` and start/restart the agent:

```sh
uv run --frozen uvicorn gopstop_agent.main:app --app-dir src --host 127.0.0.1 --port 8000 --log-config logging.json
```

In another terminal at `agent/`, test the real HTTP flow once:

```sh
uv run --frozen python -m gopstop_agent.smoke --chat > target/e2e-agent.json
```

It verifies CORS for the first configured origin, POSTs one short hike, GETs its saved
route and reads the successful exchange from Valkey. Reports include route/place UUIDs
and a hashed session label. Clarification/no-route is valid chat but fails route acceptance.
Saved places/routes and the expiring exchange remain as evidence. Failed work can also
leave committed data: do not automatically repeat an uncertain POST.
Route creation can reuse the required ORS cache; a successful hit does not validate a
new ORS key. Murat verifies that key with a bounded diagnostic miss, without cache bypass.

## Browser and full Tatras acceptance

Set `VITE_USE_MOCKS=false`, service URLs and matching CORS; restart Vite.
Run the runbook's Tatras message and another region. Check track, endpoint/stop sources,
marker reset, follow-up language/history and clarification clearing old routes.
Record main SHA, reports and browser evidence before marking E3/E5 complete.
Several model calls share Groq's free token budget. The per-worker transport serializes
calls and waits conservatively on quota headers; it does not retry 429 or coordinate
other workers/accounts. Actual limits/latency need measurement. CI uses fixtures only.
