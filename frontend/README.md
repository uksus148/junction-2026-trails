# Frontend

React 19 + TypeScript + Vite + Tailwind 4 + MapLibre (OpenFreeMap tiles, no key needed).

```bash
npm install
npm run dev     # http://localhost:5173
npm test        # planner, preferences and intent tests (vitest)
npm run build
```

Configuration comes from the root `.env` (copy `/.env.example`):

- `VITE_USE_MOCKS=true` (default) — the app runs fully in the browser with demo data
  (Tatras route, Bratislava day plan) and live photos from Wikimedia Commons.
- `VITE_USE_MOCKS=false` — calls the real services at `VITE_API_BASE_URL` and `VITE_AGENT_BASE_URL`.

Where things live:

- `src/types.ts` — the API contract shared with `api` and `agent`.
- `src/lib/planner.ts` — reference day planner (backend ports it 1:1; behaviour is pinned by `planner.test.ts`).
- `src/lib/intent.ts` — mock-mode parsing of day-plan requests and preferences (the agent does this with an LLM).
- `src/api/mock*.ts` — in-browser stand-in for the backends.
