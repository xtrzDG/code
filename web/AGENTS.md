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
- Every UI text goes into the dictionaries in Georgian, Russian, English,
  Hebrew and German: shared texts in `src/i18n/messages/en.ts`, `ru.ts`,
  `ka.ts`, `he.ts`, `de.ts`, section texts in `src/i18n/messages/sections/*/`
  (one file per namespace and language, composed in `sections/*.ts`); no
  hard-coded strings in components.
- The cabinet reads right to left in Hebrew (`<html dir="rtl">`): use
  logical classes (`ms-2`, `ps-3`, `start-0`, `text-start`, `border-s`,
  `rounded-e-lg`), never physical ones (`ml-2`, `left-0`, `text-left`); a
  vitest policy test enforces it and `node --no-warnings scripts/rtl-codemod.mjs`
  rewrites a file. Directional icons (arrows, chevrons) get `rtl:-scale-x-100`.
- Dates, times and money: Intl helpers in `src/lib/format.ts` /
  `useBusinessFormat()`, in the business time zone and currency. API
  timestamps are microseconds, prices are minor units. Any other format in a
  UI language goes through `src/lib/intl/formatters.ts` (Chrome has no
  Georgian Intl), never `new Intl.*(locale)`.
- Use the UI kit in `@/components/ui` and the semantic color tokens of
  `src/app/globals.css`.
- After a backend API change: `npm run gen:api` and commit `openapi.json`
  and `src/api/schema.d.ts`.
- Before committing: `npm run lint && npm run typecheck && npm test && npm run build`;
  after changing a flow, also `npm run e2e` (Playwright, see README).
