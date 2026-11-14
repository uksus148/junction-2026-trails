# Groq integration test

Use one worker and one tester initially. Follow the accepted D1-D5 contract and
[runbook](../docs/INTEGRATION_RUNBOOK.md). E1/E2 merged in #45/#43; deploy reviewed
code and Flyway V3. #47 added Groq; actual access remains a team-machine check.

## Configure the root environment

Preserve private values in ignored root `.env`; copy missing settings from `.env.example`:

```dotenv
AGENT_LLM_PROVIDER=groq
GROQ_API_KEY=
EXA_API_KEY=
AGENT_GROQ_MODEL=openai/gpt-oss-20b
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

After the provider/schema fixes are reviewed/merged, the API is migrated and E4 passes on the team's machine,
set `AGENT_CHAT_ENABLED=true` in root `.env` and start/restart the agent:

For Groq free limits, allow at least a minute after preflight for tokens to replenish;
preflight and the server are separate processes sharing the same account budget.

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

Measure the required intermediate-stop request after the short smoke:
```sh
uv run --frozen python -m gopstop_agent.smoke --chat --message "I want to hike from Štrbské Pleso to Rysy via the Skok waterfall. I love wild scenery." > target/e2e-tatras.json
```
Record `elapsedMs`, stage logs and the revision. Serialized Groq calls/quota waits can
exceed discovery's 90-second budget. Demo activation needs this measurement and suitable
proxy limits; direct-hike/fixture success is insufficient.

Set `VITE_USE_MOCKS=false`, service URLs and matching CORS; restart Vite.
Run the runbook's Tatras message and another region. Check track, endpoint/stop sources,
marker reset, follow-up language/history and clarification clearing old routes.
Record main SHA, reports and browser evidence before marking E3/E5 complete.
Several model calls share Groq's free token budget. The per-worker transport serializes
calls and waits conservatively on quota headers; it does not retry 429 or coordinate
other workers/accounts. Actual limits/latency need measurement. CI uses fixtures only.

## Recheck issue #48

Main `08726c3` fails live `resolve_place` with Groq 400 `tool_use_failed`.
The fix sends an inline nullable object schema with `name`, `geocodeQuery`,
`sourceIndex` and `tags`, instead of a `$ref` to `SourceResolution`. A supported
tool result still has this shape (names/query must come from supplied evidence):

```json
{"place":{"name":"Skok waterfall","geocodeQuery":"Skok waterfall, High Tatras, Slovakia","sourceIndex":0,"tags":["waterfall"]}}
```

After review, deploy the fix, restart the agent and record the tested commit.
Keep `AGENT_GROQ_MODEL=openai/gpt-oss-20b`. Repeat the preflight above: it calls
resolution directly, without the shared resolution cache. `checks` must include
`llm_resolution`; a failed run at that stage remains a blocker. `place:null` is a
valid unresolved response, so a passing preflight alone does not prove location accuracy.
Do not flush shared caches: the changed prompt already invalidates old resolution keys.

After quota replenishes, repeat the short chat smoke, then the full Tatras command
and Daniil's browser matrix. Record status, stage, elapsedMs, created IDs and revision;
keep raw provider errors/keys out of public reports. The separate ORS no-route result
for Rysy is tracked in [#49](https://github.com/uksus148/trego./issues/49) and needs
Murat's investigation. Popradské Pleso is a useful control hike,
but success there does not complete the required Tatras acceptance.
