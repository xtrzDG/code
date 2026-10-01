# Assistant Workshop — owner cabinet (web)

The owner cabinet of the AI front-line assistant: sign-in by phone (any country)
or e-mail, businesses, the six-step profile wizard, every business section of
concept section 8 (dashboard, conversations, bookings, leads, handoffs,
knowledge, assistant, channels, billing, settings) and the platform admin.
Next.js (App Router) + TypeScript (strict) + Tailwind CSS v4.
Interface languages: Georgian (`ka`), Russian (`ru`), English (`en`).

The browser never talks to the Python API directly and never sees the bearer
token: every call goes through the cabinet's own route handlers (a
backend-for-frontend), which keep the token in an httpOnly cookie.

## Run

Requirements: Node 22.12+ and npm 10; the backend from the repository root.

```bash
# 1. the API (repository root), in-memory storage, login codes printed to its log
uv sync
APP_ENV=development uv run uvicorn app.main:create_application --factory --port 8000

# 2. the cabinet
cd web
cp .env.example .env.local      # BACKEND_URL=http://localhost:8000
npm ci
npm run dev                     # http://localhost:3000
```

Sign in with any mobile number of a supported country (or an e-mail); in
development the 6-digit code appears in the API log
(`Login code 123456 for … Code logging is for development only.`).

### Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKEND_URL` | `http://localhost:8000` | Base URL of the Python API, used only on the server (route handlers, proxy, Server Components). |
| `COOKIE_SECURE` | `true` in production | `false` serves the session cookie without `Secure` (a production build over plain HTTP). |

Behind a reverse proxy, run the API with
`--proxy-headers --forwarded-allow-ips=<address of this web server>`: the cabinet
forwards `X-Forwarded-For`, so the audit log keeps the client's address.

## Scripts

| Script | What it does |
| --- | --- |
| `npm run dev` / `build` / `start` | Next.js development server, production build, production server |
| `npm run lint` | ESLint (`eslint-config-next` + strict project rules), zero warnings allowed |
| `npm run typecheck` | `next typegen` (route types) + `tsc --noEmit` |
| `npm test` | Vitest unit tests (`src/**/*.test.ts`) |
| `npm run e2e` | Playwright end-to-end tests against the real API (see [End-to-end tests](#end-to-end-tests)) |
| `npm run gen:api` | Regenerate `openapi.json` from the backend (`uv run python -m scripts.export_openapi`) and `src/api/schema.d.ts` from it (openapi-typescript). Run after any backend API change and commit both files. |

All of `npm run lint && npm run typecheck && npm test && npm run build` must pass
(CI job "web"); the CI job "e2e" then runs `npm run e2e`.

## End-to-end tests

`web/e2e/` drives the built cabinet in Chromium against the real Python API:

```bash
cd web
npx playwright install chromium   # once (CI: --with-deps)
npm run e2e                       # builds the cabinet, starts API + cabinet, runs e2e/*.spec.ts
E2E_SKIP_BUILD=1 npm run e2e      # reuse the last `next build`
npm run e2e -- onboarding         # one file
```

- `e2e/playwright.config.ts` starts the API from the repository root
  (`uv run uvicorn …`, `APP_ENV=development`, in-memory storage, login-code
  providers blanked) with its output in `e2e/.artifacts/api.log`, and the
  cabinet with `next build && next start`. Each run starts from empty data.
- Sign-in codes are read from that log (`e2e/support/login-codes.ts`); the
  `account` and `owner` fixtures (`e2e/support/fixtures.ts`) sign up through
  the API and put the session cookie into the browser, so only the sign-in
  tests type codes.
- Every test fails on a browser console error or an uncaught exception;
  `consoleErrors.allow(/…/)` accepts one a test provokes on purpose.
- Selectors are roles and labels with texts from the cabinet's own
  dictionaries (`e2e/support/messages.ts`), so rewording a text does not break
  a test. Prefer `getByRole`/`getByLabel`; avoid CSS classes.
- Scenarios: sign-in with a German number and with e-mail (and a wrong code),
  a business in Turkey with Turkish, English and Arabic, a failed save shown
  above the open dialog, the six wizard steps, every section from the sidebar
  and from the phone menu (no sideways scrolling at 390 px), switching the
  interface language ru/ka/en, the website chat demo page of the API.

| Variable | Default | Meaning |
| --- | --- | --- |
| `E2E_API_PORT` / `E2E_WEB_PORT` | `8010` / `3010` | Ports of the API and the cabinet under test |
| `E2E_SKIP_BUILD` | — | `1`: start the existing `.next` build |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | — | A Chromium already on the machine instead of Playwright's download (the suite pins `@playwright/test` 1.56.1, Chromium 141) |

Failures leave screenshots and traces in `e2e/.artifacts/results/`
(`npx playwright show-trace <trace.zip>`); CI uploads them with the HTML report
and the API log as the `e2e-report` artifact.

## Structure

```text
web/
  openapi.json                 API description exported from the backend (generated)
  e2e/                         Playwright end-to-end tests (playwright.config.ts, *.spec.ts, support/)
  src/
    proxy.ts                   runs before pages: sign-in redirects, current path header, language cookie
    app/                       routes (App Router)
      layout.tsx               <html lang>, I18nProvider, ToastProvider
      login/                   sign-in by phone (country picker) or e-mail, 6-digit code
      businesses/              list and creation of businesses (a new account gets the form at once)
      b/[businessId]/          one business: layout.tsx loads it + the user and renders the sidebar
        onboarding/            the six-step profile wizard (?step=…) and "what to add" (+ _components/)
        dashboard/             next step, KPI tiles for a period (?period=), package usage, breakdowns
        conversations/         list + detail side by side (layout.tsx), [conversationId]/ on phones
        bookings/              bookings by day, manual booking with free slots, details, move, cancel
        leads/                 requests by status, status changes, details
        handoffs/              open/resolved handoffs by urgency, resolve
        knowledge/             items (layout.tsx: tabs) + questions/ (unanswered), import/ (menu
                               photo, PDF or link), resources/ (bookable resources, special days)
        assistant/             test chat (layout.tsx: live version + tabs), versions/,
                               versions/[versionId]/ (go-live checklist, autotests, publish, rollback)
        channels/              chat channels, website chat code, call forwarding, Google Calendar,
                               staff Telegram link
        billing/               plan, trial, usage, plans of the country, invoices, payment
        settings/              tabs in the URL hash: general, team, notifications, privacy, audit
      admin/                   platform admin: clients (filters, sorts) and clients/[businessId]/
      api/
        auth/start|verify|logout|expired   sign-in route handlers (cookie handling)
        backend/[...path]      BFF proxy: /api/backend/v1/... -> BACKEND_URL/v1/...
        locale                 switch the interface language (cookie + PATCH /v1/me)
    api/                       typed API access
      schema.d.ts              generated by openapi-typescript (do not edit)
      types.ts                 named types: Schema<"BookingView">, RequestBody<path, method>, aliases
      client.ts                `api`: openapi-fetch client for Client Components (via the BFF)
      hooks.ts                 useApiQuery / useApiMutation
      catalog.ts               useCountries / useCountryProfile / useNiches
      errors.ts                ApiError, error codes, localized messages
      result.ts                unwrap(): data or a thrown ApiError
      auth.ts                  startLogin / verifyLogin (browser)
    server/                    server-only code
      api.ts                   getServerApi(), serverFetch(), getCurrentUser(), getBusiness()
      backend.ts               BACKEND_URL, cookies, header allow-lists, CSRF check
      relay.ts                 streaming relay used by the route handlers
    i18n/                      config.ts (locales, negotiation), translate.ts, server.ts, client.tsx
      messages/en.ts ru.ts ka.ts   shared texts (common, auth, nav, onboarding, errors …); English is the reference
      messages/sections/       section texts, spread into en/ru/ka: insights.ts (dashboard, conversations,
                               bookings, leads, handoffs), content.ts (knowledge, assistant),
                               workspace.ts (channels, billing, settings, admin)
    components/
      ui/                      the UI kit (import from "@/components/ui"): Button, ButtonLink, Input,
                               Select, Textarea, Checkbox, Radio, Field, Fieldset, Card, Table, Badge,
                               Modal, Drawer, useModalDialog, Toast, EmptyState, ErrorState, Spinner,
                               LoadingBlock, PageHeader, Alert
      shell/                   ShellFrame (sidebar + phone menu), BusinessShell, AdminShell, TopBar
      business/                BusinessContext (useBusiness, useBusinessFormat), status badges,
                               sectionMetadata (page titles)
      insights/                shared by dashboard … handoffs: status badges and label maps, segmented
                               control, confirm and customer-message dialogs, show-more/refresh,
                               business-local dates, replaceUrlQuery, useAutoReload
      content/                 shared by knowledge and assistant: SectionTabs (route tabs), Tabs,
                               ConfirmDialog, Switch, icons, subPageMetadata
      workspace/               shared by channels, billing, settings, admin: CopyButton, ConfirmDialog
                               with typed confirmation, InlineError, hash Tabs (useHashTab), UsageMeter,
                               Facts, OwnerOnly notes, channel names, helpers
      BusinessSwitcher.tsx LanguageSwitcher.tsx CountrySelect.tsx icons.tsx
    lib/                       pure helpers with unit tests (*.test.ts): navigation (sections, paths,
                               safeNextPath), format (Intl, money units), countries (phone/country),
                               hours (opening hours), wizard (profile answers), knowledge, resources,
                               assistant, validation (zod), classMerge (className overrides), cn
```

## Sections

| Section | Path | What the owner does there |
| --- | --- | --- |
| Profile | `onboarding?step=…` | Six steps (niche and languages, contacts and hours, offer, booking rules, FAQ and handoff, channels), each saved on its own; the "what to add" summary opens the full list in a side panel |
| Dashboard | `dashboard?period=…` | The next step for the business status, KPI tiles, package minutes and dialogs, languages/channels/handoff reasons |
| Conversations | `conversations[/{id}]` | Filters kept in the URL, transcript with tool calls, linked bookings, leads and handoffs |
| Bookings | `bookings` | Day groups, manual booking with free slots, confirm / complete / no-show / move / cancel and the customer text |
| Leads | `leads` | Status tabs, inline status change, details |
| Handoffs | `handoffs` | Open first by urgency, resolve, call and conversation links |
| Knowledge | `knowledge`, `/questions`, `/import`, `/resources` | Items and search, unanswered questions to FAQ, menu import with review, resources and special days |
| Assistant | `assistant`, `/versions`, `/versions/{id}` | Test chat, versions, go-live checklist, autotests, publish and rollback |
| Channels | `channels` | Connect messengers, website chat snippet, call forwarding codes, Google Calendar, staff Telegram link |
| Billing | `billing` | Trial, plan change, usage meters, invoices, payment (owners only) |
| Settings | `settings#general`, `#team`, `#notifications`, `#privacy`, `#audit` | Business settings and pause, team, manager contacts, data processing agreement and customer data, audit log |
| Admin | `/admin`, `/admin/clients/{id}` | Platform admins: all clients, health, opening a client's cabinet |

## Conventions

### Adding a business page

1. Every section of concept section 8 already has its page; extend it in its
   folder. A new section gets `src/app/b/[businessId]/<section>/page.tsx`, an
   entry in `BUSINESS_SECTIONS` and `BUSINESS_SECTION_LABELS`
   (`src/lib/navigation.ts`) and an icon in `SECTION_ICONS`
   (`src/components/shell/BusinessShell.tsx`); the e2e suite then opens it too.
2. Keep `page.tsx` a small Server Component: metadata + one client screen.

   ```tsx
   // src/app/b/[businessId]/bookings/page.tsx
   import { sectionMetadata } from "@/components/business/SectionPlaceholder";
   import { BookingsScreen } from "./BookingsScreen";

   export const generateMetadata = sectionMetadata("bookings");

   export default function BookingsPage() {
     return <BookingsScreen />;
   }
   ```

3. Put interactive parts in `"use client"` components next to the page
   (`BookingsScreen.tsx`, helpers in a `_components/` folder). They get the
   business and the user from the layout:

   ```tsx
   const { business, me, isOwner, isPlatformAdmin } = useBusiness();
   const format = useBusinessFormat(); // format.dateTime(us), format.money(minor), format.date, format.time
   ```

4. Start the screen with `<PageHeader title=… description=… actions=… />`, use
   `Card`, `Table`, `Badge`, `EmptyState`, `ErrorState`, `LoadingBlock` from
   `@/components/ui`. Owner-only actions: hide or disable them unless `isOwner`
   (the API answers 403 anyway). Reuse the section folders in `components/`
   (`insights`, `content`, `workspace`) before writing another dialog or badge.
5. Filters and tabs that belong in the address: write the query with
   `replaceUrlQuery` (`components/insights/urlQuery.ts`) or
   `window.history.replaceState(null, "", url)` and read it with
   `useSearchParams()`. Never pass `window.history.state`: it carries Next's
   own marker and the router then ignores the change.

### UI kit notes

- `Modal` and `Drawer` (side panel) are native modal `<dialog>`s driven by
  `open`. `onClose` runs only when the person closes them (Escape, close
  button, backdrop), not when `open` turns false, so one dialog can replace
  another. Own `<dialog>`s use `useModalDialog(open, onClose)` for the same.
- Toasts move into the topmost open modal dialog, so a failed save inside a
  dialog is visible and can be dismissed.
- `Alert`'s `action` sits beside the text when the alert is wide and under it
  when it is narrow (a container query).
- `className` on `Button`, `ButtonLink`, `Input` and `Textarea` replaces the
  component's own width, height, padding, radius, font size and colour
  classes of the same kind (`w-40`, `text-danger`, `hover:bg-…`; see
  `lib/classMerge.ts`). Destructive quiet buttons: `variant="danger-ghost"`.
- Customer texts (names, messages, questions) get `dir="auto"`.

### Calling the API

Client Components use the typed `api` client (requests go to `/api/backend/*`,
the BFF adds the token). Paths, parameters and bodies are checked against
`openapi.json`:

```tsx
import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";

const bookings = useApiQuery(
  () =>
    api.GET("/v1/businesses/{business_id}/bookings", {
      params: { path: { business_id: business.id }, query: { status: "confirmed" } },
    }),
  [business.id], // reloads when these change, like useEffect
);
// bookings.data, bookings.isLoading, bookings.error (ApiError), bookings.reload(), bookings.setData()

const cancel = useApiMutation((bookingId: string) =>
  api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/cancel", {
    params: { path: { business_id: business.id, booking_id: bookingId } },
  }),
  { errorMessages: { conflict: "bookings.alreadyCancelled" } }, // optional context texts
);
const result = await cancel.run(id); // failures are shown as a localized toast
if (result.ok) bookings.reload();
```

- Types: `Schema<"BookingView">`, aliases in `src/api/types.ts`,
  `RequestBody<"/v1/businesses/{business_id}/bookings", "post">` for bodies.
- Timestamps from the API are UNIX **microseconds**; money is an integer in
  **minor units** of the business currency (`format.money(minor)`,
  `majorToMinor` / `minorToMajor` in `src/lib/format.ts`).
- Anything that is not a single call: `await unwrap(api.GET(...))` returns the
  data or throws `ApiError` (`status`, `code`, `detail`, `requestId`).
- Server Components: `const api = await getServerApi(); const data = await
  serverFetch(api.GET(...));` (`src/server/api.ts`). 401 sends the user to sign
  in, 404 shows the not-found page. `getCurrentUser()` and `getBusiness(id)`
  are cached per request.
- Never call `BACKEND_URL` from the browser and never put the token in client
  code; new server-side endpoints go into `src/app/api/*` route handlers using
  `src/server/relay.ts`.
- After a backend change: `npm run gen:api`, then fix the type errors it shows.

### Errors

The backend answers `{"error": "<code>", "message": "<English>"}`. The UI shows
the localized text of the code (`errors.codes.*`): `toast.error(error)` or
`<ErrorState error={error} onRetry={reload} />`. For context-specific wording
pass overrides: `toast.error(error, { access_denied: "auth.errors.countryRestricted" })`.
The English backend message is shown as a detail only for `validation_failed`
and `conflict`.

### Translations

- Shared texts (common, auth, nav, pages, onboarding, errors, validation) live
  in `src/i18n/messages/{en,ru,ka}.ts`; section texts in
  `src/i18n/messages/sections/{insights,content,workspace}.ts`, whose
  `*En`/`*Ru`/`*Ka` objects are spread into those files. English is the
  reference; `ru` and `ka` are typed as `Messages`, so a key added in English
  and missing in another language fails `npm run typecheck` (and a unit test).
  At runtime a missing text falls back to English, then to the key.
- Top-level keys are namespaces and must not clash between the files. An
  object with a key named `other` is read as plural forms, so do not use
  `other` as an ordinary key (e.g. `leads.type.otherRequest`).
- Client Components: `const { t, tp, locale } = useI18n();` —
  `t("bookings.title")`, `t("onboarding.stepOf", { number: 2, total: 6 })`,
  plurals `tp("onboarding.gaps.times", count)` with Intl plural categories
  (`one`/`few`/`many`/`other`; Russian needs `few` and `many`).
- Server Components: `const { t } = await getI18n();` (`@/i18n/server`).
- Keys are checked by TypeScript (`MessageKey`); for keys built at runtime
  keep a `Record<EnumValue, MessageKey>` map (see `BusinessStatusBadge.tsx`).
- Add a section's texts under its own namespace (`bookings.*`, `leads.*`) in
  its section file, sidebar labels under `nav.*`, page descriptions under
  `pages.*`.
- Pass `language: locale` to API calls that return display texts (catalog,
  wizard, gaps); the BFF also sends `Accept-Language` with the interface language.
- Dates, times, numbers and money: Intl only (`src/lib/format.ts`,
  `useBusinessFormat()`), in the business time zone and currency.

The interface language is chosen by the `aw_locale` cookie (set at sign-in from
the account language, by the language switcher, or by the proxy from
`GET /v1/me`), else the browser's `Accept-Language`, else English.

### Forms

- Wrap controls in `<Field label hint error required>{(control) => <Input {...control} />}</Field>`
  (labels, `aria-describedby` and `aria-invalid` are wired for you); groups of
  checkboxes or radios go in `<Fieldset legend>`.
- Validate with zod; messages are i18n keys (`messageKey("validation.required")`,
  `fieldErrors(result)` in `src/lib/validation.ts`).
- Phone numbers of any country are sent as typed with the country as a hint
  (`country_hint`); the API parses them. `CountrySelect` lists countries from
  `GET /v1/catalog/countries` in the interface language.

### Styling

Tailwind CSS v4 with semantic tokens defined in `src/app/globals.css`
(`bg-canvas`, `bg-surface`, `bg-surface-muted`, `text-ink`, `text-ink-muted`,
`text-ink-subtle`, `border-line`, `bg-accent-solid`, `text-accent`,
`bg-accent-soft`, `text-success|warning|danger|info` and `-soft` backgrounds).
They follow the system light/dark scheme, so `dark:` variants are rarely
needed. Layouts are mobile-first: the sidebar becomes a drawer below `lg`.
Use semantic HTML, visible focus, and labels for icon-only buttons.

## Security notes

- Session: httpOnly, `SameSite=Lax`, `Secure` in production cookie `aw_session`
  holding the API bearer token; expires with the API session. A 401 from the
  API clears it.
- The BFF forwards only `/v1/*` paths, an allow-list of headers (never the
  browser's cookies), and refuses cross-site state-changing requests
  (`Origin`/`Sec-Fetch-Site` check) on top of `SameSite=Lax`.
- After sign-in the cabinet only redirects to same-site paths (`safeNextPath`).
