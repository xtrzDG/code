<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Owner cabinet: rules for agents

Read `README.md` in this folder first (structure, adding a page, calling the
API, translations). In short:

- Browser code calls the API only through `api` from `@/api/client`
  (the BFF at `/api/backend/*`); never `BACKEND_URL`, never the token.
- Every UI text goes into `src/i18n/messages/en.ts`, `ru.ts` and `ka.ts`
  (Georgian, Russian, English); no hard-coded strings in components.
- Dates, times and money: Intl helpers in `src/lib/format.ts` /
  `useBusinessFormat()`, in the business time zone and currency. API
  timestamps are microseconds, prices are minor units.
- Use the UI kit in `@/components/ui` and the semantic color tokens of
  `src/app/globals.css`.
- After a backend API change: `npm run gen:api` and commit `openapi.json`
  and `src/api/schema.d.ts`.
- Before committing: `npm run lint && npm run typecheck && npm test && npm run build`.
