# trego. Frontend

React 19 + TypeScript + Vite + Tailwind 4 + MapLibre (OpenFreeMap tiles, no key needed).

```bash
npm install
npm run dev     # http://localhost:5173
npm test        # vitest
npm run build
```

Configuration comes from the root `.env` (copy `/.env.example`):

- `VITE_USE_MOCKS=true` (default) — the app runs fully in the browser with the Tatras demo route
  and live, attributed photos from Wikimedia Commons.
- `VITE_USE_MOCKS=false` — calls the real services at `VITE_API_BASE_URL` and `VITE_AGENT_BASE_URL`.

Where things live:

- `src/types.ts` — the API contract shared with `api` and `agent` (mirrors the root CLAUDE.md).
- `src/api/` — real client (`realApi.ts`) and the in-browser mock (`mock.ts`, `mockStore.ts`, `wikimedia.ts`).
- `src/components/` — map, chat, manual planning, photos along the route.
