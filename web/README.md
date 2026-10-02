# Assistant Workshop — owner cabinet (web)

The owner cabinet of the AI front-line assistant and its public landing page:
the product, prices by country and FAQ at `/`, sign-in by phone (any country)
or e-mail, businesses, the six-step profile wizard, every business section of
concept section 8 (dashboard, conversations, bookings, leads, handoffs,
knowledge, assistant, channels, billing, settings) and the platform admin.
Next.js (App Router) + TypeScript (strict) + Tailwind CSS v4.
Interface languages: Georgian (`ka`), Russian (`ru`), English (`en`).
Colour themes: dark (the default), light and the system's setting.

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
| `TRUSTED_PROXY_HOPS` | `0` | How many right-most `X-Forwarded-For` entries the cabinet's own proxies add (Render: `1`). Only those are forwarded to the API; the rest of the header comes from the browser and could be forged. `0` forwards no client address. |

Behind a reverse proxy, run the API with
`--proxy-headers --forwarded-allow-ips=<address range of this web server>` (never
`*`): the cabinet forwards the client address its proxies vouch for
(`TRUSTED_PROXY_HOPS`), so the audit log keeps the client's address.

## Scripts

| Script | What it does |
| --- | --- |
| `npm run dev` / `build` / `start` | Next.js development server, production build, production server |
| `npm run lint` | ESLint (`eslint-config-next` + strict project rules), zero warnings allowed; every file in `src/` and `e2e/` has at most 300 lines (`max-lines`; the generated `schema.d.ts` and `*.generated.ts` are exempt) |
| `npm run typecheck` | `next typegen` (route types) + `tsc --noEmit` |
| `npm test` | Vitest unit tests (`src/**/*.test.ts`) |
| `npm run e2e` | Playwright end-to-end tests against the real API (see [End-to-end tests](#end-to-end-tests)) |
| `npm run gen:api` | Regenerate `openapi.json` from the backend (`uv run python -m scripts.export_openapi`) and `src/api/schema.d.ts` from it (openapi-typescript). Run after any backend API change and commit both files. It also runs `gen:currencies` and `gen:names`. |
| `npm run gen:currencies` | Regenerate `src/lib/currencyDigits.generated.ts`: the digits after the decimal point of every currency, from the backend's CLDR data (Babel). Money is converted between minor and major units with this table, not with the browser's Intl data, which differs between browser versions. A backend test fails when the file is stale. |
| `npm run gen:names` | Regenerate `src/lib/displayNames.generated.ts`: country and language names in Georgian, Russian and English from the backend's CLDR data. `countryName` and `languageName` read it before Intl: Chrome has no Georgian display names, so the server and the browser would disagree (a hydration error) and Georgian owners would see codes. A backend test fails when the file is stale. |

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
- Scenarios that need the voice platform or Meta (a call recording, a WhatsApp chat past its
  24-hour window) answer the card's own BFF calls with `page.route`
  (`e2e/card-recordings.spec.ts`, `e2e/card-whatsapp.spec.ts`, served by
  `e2e/support/conversation-card.ts`); the widget tests run the API's
  `/widget.js` on a fake host site (`e2e/support/widget-site.ts`).
- Scenarios: the landing page (prices of a chosen country, theme and language
  kept after a reload, signed-in users sent to their businesses),
  sign-in with a German number and with e-mail (and a wrong code),
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
      layout.tsx               <html lang data-theme> from the cookies, I18nProvider, ThemeProvider,
                               ToastProvider; the browser's theme-color
      globals.css              design tokens (colours of both themes, radii, shadows), `dark:` variant
      page.tsx                 "/": the public landing page (signed-in users go to /businesses)
      _landing/                its sections: Hero (+ HeroChat), Facts, Steps, Features, Channels, Niches,
                               World, Pricing (+ PlanCard, CountryPicker), Faq, FinalCta, header, footer;
                               landingData.ts reads the public catalog on the server
      robots.ts                robots.txt: only "/" is for search engines
      login/                   sign-in by phone (country picker, only the code channels that work now)
                               or e-mail, 6-digit code: LoginScreen (layout), _components/ (DestinationForm,
                               PhoneFields, CodeForm), _lib/ (useLoginFlow, useDestination, loginTexts,
                               loginOptions)
      businesses/              list and creation of businesses (a new account gets the form at once):
                               CreateBusinessForm, _components/ (CountryDefaults, CreatedSummary),
                               _lib/ (useCreateBusiness, languageOptions)
      b/[businessId]/          one business: layout.tsx loads it + the user and renders the sidebar
        onboarding/            the six-step profile wizard (?step=…) and "what to add" (+ _components/)
        dashboard/             next step, KPI tiles for a period (?period=), daily trend chart (plain SVG),
                               package meters (owners and staff), breakdowns
        conversations/         server-paged feed with filters + card (calls with a recording player,
                               rating, linked bookings/leads/handoffs, staff reply box, WhatsApp
                               template after 24 hours); layout.tsx keeps the feed mounted beside
                               the card, [conversationId]/ on phones
        bookings/              server-paged bookings by day ("show more"), manual booking with free
                               slots (whole-day mode), details, edit, move, cancel
        leads/                 server-paged requests by status with tab counts, status changes, details
        handoffs/              server-paged open/resolved handoffs by urgency, resolve
        knowledge/             items (layout.tsx: tabs; server-paged, filtered by the API) + questions/
                               (unanswered, server-paged), import/ (menu photo, PDF or link; discard a
                               whole batch), resources/ (bookable resources, special days)
        assistant/             test chat (layout.tsx: live version + tabs), versions/,
                               versions/[versionId]/ (go-live checklist, autotests with live progress,
                               publish, rollback)
        channels/              chat channels (with the platform's last error; WhatsApp's template for
                               staff replies), website chat code and look, call forwarding, Google
                               Calendar (state, last sync), staff Telegram link
        billing/               plan, trial, usage, plans of the country, invoices, payment
        settings/              tabs in the URL hash: general, team, notifications, privacy, audit
      admin/                   platform admin: clients (filters, sorts) and clients/[businessId]/
      api/
        auth/start|verify|logout|expired   sign-in route handlers (cookie handling)
        backend/[...path]      BFF proxy: /api/backend/v1/... -> BACKEND_URL/v1/... (JSON, and audio
                               of call recordings streamed with its type and length; Range and
                               If-Range go up, Accept-Ranges and Content-Range come back)
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
      theme.ts                 getTheme(): the aw_theme cookie of the request
      backend.ts               BACKEND_URL, cookies, header allow-lists, CSRF check
      relay.ts                 streaming relay used by the route handlers
    i18n/                      config.ts (locales, negotiation), translate.ts, server.ts, client.tsx
      messages/en.ts ru.ts ka.ts   shared texts (common, auth, nav, theme, errors …); English is the reference
      messages/onboarding/     the profile wizard's texts, one file per language
      messages/landing/        the landing page's texts, one file per language
      messages/sections/       section texts, spread into en/ru/ka: insights.ts (dashboard, conversations,
                               bookings, leads, handoffs), content.ts (knowledge, assistant),
                               workspace.ts (channels, billing, settings, admin); each composes one file
                               per namespace and language from its folder (insights/bookings.ru.ts)
    components/
      ui/                      the UI kit (import from "@/components/ui"): Button, ButtonLink, Input,
                               Select, Textarea, Checkbox, Radio, Field, Fieldset, Card, Table, Badge,
                               Modal, Drawer, useModalDialog, Toast, EmptyState, ErrorState, Spinner,
                               LoadingBlock, PageHeader, Alert
      shell/                   ShellFrame (frame), Sidebar (navigation, user), ShellTopBar (business / section,
                               language and theme), BusinessShell, AdminShell, TopBar (pages outside a
                               business), Brand, SignOutButton
      theme/                   ThemeProvider (useTheme) and ThemeSwitcher (dark / light / system)
      business/                BusinessContext (useBusiness, useBusinessFormat), status badges,
                               sectionMetadata (page titles)
      insights/                shared by dashboard … handoffs: status badges and label maps, segmented
                               control, confirm and customer-message dialogs, usePagedQuery (keyset
                               paging with "show more" that keeps its length on reload), LoadMore,
                               refresh, business-local dates, useToday (moves on at the business's
                               midnight), replaceUrlQuery, useAutoReload (lists whose every load
                               is audited pass `intervalMs: null` and reload only on return)
      content/                 shared by knowledge and assistant: SectionTabs (route tabs), Tabs,
                               ConfirmDialog, Switch, icons, subPageMetadata, usePagedList
                               ({items, next_cursor} lists with "show more")
      workspace/               shared by channels, billing, settings, admin: CopyButton, ConfirmDialog
                               with typed confirmation, InlineError, hash Tabs (useHashTab), UsageMeter,
                               Facts, OwnerOnly notes, channel names, useCursorList (paged API lists
                               with "show more"), MarkdownDocument (renders the DPA text without
                               HTML), helpers (zoned dates, usage)
      BusinessSwitcher.tsx LanguageSwitcher.tsx CountrySelect.tsx icons.tsx
    lib/                       pure helpers with unit tests (*.test.ts): navigation (sections, paths,
                               safeNextPath), format (Intl, money units), countries (phone/country),
                               hours (opening hours), wizard/ (niche answers, offers, FAQ), knowledge/
                               (kinds, item form, menu import), resources, assistant/ (versions,
                               autotests, go-live, test chat), validation (zod), classMerge (className
                               overrides), cn, theme (cookie, theme colours), landing (country guess,
                               plan prices)
```

## Sections

| Section | Path | What the owner does there |
| --- | --- | --- |
| Profile | `onboarding?step=…` | Six steps (niche and languages, contacts and hours, offer, booking rules, FAQ and handoff, channels), each saved on its own; the "what to add" summary opens the full list in a side panel |
| Dashboard | `dashboard?period=…` | The next step for the business status, KPI tiles, a daily trend chart with a table view, package minutes and dialogs (staff too, without prices), languages/channels/handoff reasons |
| Conversations | `conversations[/{id}]` | Server filters and search kept in the URL, transcript with tool calls and calls (a recording is downloaded once and audited when "Play recording" is pressed, then plays and seeks from memory; an expired session goes to sign-in, a deleted recording says so), rating, linked bookings, leads and handoffs, staff reply (after the WhatsApp 24-hour window: in the owner's approved template, or a pointer to Channels; a template WhatsApp refuses says what to fix), booking confirmation prefilled into the reply box whenever it can send it, booking for the customer |
| Bookings | `bookings` | Server-paged day groups with place and order filters, manual booking with free slots (whole day), edit, confirm / complete / no-show / move / cancel and the customer text |
| Leads | `leads` | Server-paged status tabs with counts, inline status change, details |
| Handoffs | `handoffs` | Open first by urgency, resolve, call and conversation links |
| Knowledge | `knowledge`, `/questions`, `/import`, `/resources` | Server-paged items and search, unanswered questions to FAQ, menu import with review and batch discard, resources and special days |
| Assistant | `assistant`, `/versions`, `/versions/{id}` | Test chat with tool calls, versions, go-live checklist with fix links, autotests with live progress, publish and rollback with reasons |
| Channels | `channels` | Connect messengers and see why one stopped, WhatsApp's template for staff replies after 24 hours (name and language), website chat snippet, colour and corner, call forwarding codes, Google Calendar state and last sync, staff Telegram link |
| Billing | `billing` | Trial, subscribe with payment (after the trial, an overdue payment or a cancellation), plan change, usage meters, invoices, payment (owners only) |
| Settings | `settings#general`, `#team`, `#notifications`, `#privacy`, `#audit` | Business settings and pause, team with owner/staff roles, manager contacts, reading and accepting the data processing agreement, the customer list with export and erasure, the audit log with server filters. General and Notifications save with the business `revision` they showed (`expected_revision`); when someone saved since (another owner, the Telegram bot adding a manager), the API answers 409 `stale_revision` and the tab reloads and says so instead of overwriting. General starts from the business as stored when it opens, and after a stale refusal keeps what was typed: fields nobody else changed are saved again at once, fields changed on both sides show the stored value |
| Admin | `/admin`, `/admin/clients/{id}` | Platform admins: all clients (server filters, sorts and paging, totals), health, opening a client's cabinet |

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
   (`BookingsScreen.tsx`; its parts in a `_components/` folder, its hooks and
   pure helpers with their tests in `_lib/`). Keep files small: one screen,
   card, dialog, hook or helper group per file, at most 300 lines (`npm run
   lint` fails on a longer one). They get the
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
- `Button` and `ButtonLink` take `leadingIcon` and `trailingIcon` (an arrow
  after the label); sizes `sm` 32 px, `md` 36 px (like inputs), `lg` 44 px.
- Customer texts (names, messages, questions) get `dir="auto"`; so do
  `Input` (text and search) and `Textarea`, so a name typed in Arabic reads
  right to left in any interface language.

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

Some refusals also carry machine-readable reasons, kept as
`ApiError.reasons` (`[{code, message, details}]`): a refused publish or
rollback names the failed go-live checks (`subscription_or_trial`, `dpa`,
`profile_gaps`, `staff_contact`, `autotests`, `voice_configuration`) or the
version state, and a menu link the API cannot read is `menu_link_invalid`,
`menu_link_unreachable` or `menu_link_unreadable`. A refused booking names
why (`closed`, `too_soon`, `time_required`, `taken`, `party_too_large`,
`no_seating_resource`; the numbers and days are in `details`). Screens map these
codes to their own texts (`refusalReasons` in `src/lib/assistant/goLive.ts`,
`menuLinkProblem` in `src/lib/knowledge/menuImport.ts`, `BOOKING_REFUSAL_MESSAGES` passed
as `reasonMessages` to `useApiMutation`); never match the English message.

### Translations

- Shared texts (common, auth, nav, theme, pages, errors, validation) live
  in `src/i18n/messages/{en,ru,ka}.ts`; section texts in
  `src/i18n/messages/sections/{insights,content,workspace}.ts`, whose
  `*En`/`*Ru`/`*Ka` objects are spread into those files; each is composed of
  one file per namespace and language in its folder
  (`sections/insights/bookings.en.ts`, `bookings.ru.ts`, `bookings.ka.ts`; a
  large namespace in a few parts); the wizard's and the landing page's in
  `messages/onboarding/` and `messages/landing/` (one file per language).
  Translations are typed `Translation<typeof …En>`. English is the
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
`GET /v1/me`), else the browser's `Accept-Language`, else English. The
language switcher (a native select showing each language by its own name)
is in the top bar of every page and in the "New business" dialog; it keeps
the current page and re-renders it in the new language.

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

Tailwind CSS v4 with semantic tokens defined in `src/app/globals.css`:

| Token | Use |
| --- | --- |
| `bg-canvas`, `bg-surface`, `bg-surface-muted` | page, cards and dialogs, quiet fills (table heads, chips, inactive tracks) |
| `text-ink`, `text-ink-muted`, `text-ink-subtle` | text, secondary text, hints and meta |
| `border-line`, `border-line-strong` | 1px hairlines between blocks; borders of form controls |
| `bg-accent-solid` (+ `-hover`, `text-on-accent`), `text-accent`, `bg-accent-soft` + `text-accent-ink` | the one accent colour: primary buttons, links, selected items |
| `text-success|warning|danger|info` and `bg-…-soft`, `bg-danger-solid` | statuses, alerts, badges, destructive buttons |
| `text-chart-1|2|3` | chart series (blue, orange, green) |
| `outline-focus` | focus rings (`:focus-visible` gets one everywhere) |

Each token holds a light and a dark value, `light-dark(<light>, <dark>)`, and
`color-scheme` picks one, so pages never need `dark:` variants (the variant
exists and follows the theme). Both themes are checked for WCAG AA: text
tokens ≥ 4.5:1 on canvas, surface and surface-muted; status colours ≥ 4.5:1
on their `-soft` backgrounds; `line-strong`, `focus` and the chart colours
≥ 3:1. The look is flat: blocks are separated by hairlines, not shadows
(`shadow-sm` is none and the larger shadows are faint), corners are
restrained (`rounded-xl` 10 px, `rounded-2xl` 12 px). Fonts are the system's
(Georgian, Cyrillic and Latin), nothing is downloaded. Layouts are
mobile-first: the sidebar becomes a drawer below `lg`. Use semantic HTML,
visible focus, and labels for icon-only buttons.

### Theme

`<html data-theme="dark | light | system">` is rendered by the root layout
from the `aw_theme` cookie (dark when there is none), so the first paint has
the right colours; "system" is `color-scheme: light dark` and follows the
operating system live. `ThemeSwitcher` (a radio group of three icons with
their names for screen readers and as tooltips) sits in the top bar of every
signed-in page, on the landing, sign-in and business list pages; it rewrites
the attribute, the cookie (a year) and `<meta name="theme-color">` without a
reload. `useTheme()` gives `{ theme, setTheme }`.

### Landing page

`/` is a Server Component for visitors without a session (signed-in users are
redirected to `/businesses`). It reads the public catalog with
`loadLandingData`: countries, niches and `GET /v1/catalog/plans` for the
country in `?country=` (else the visitor's country from `x-vercel-ip-country`
/ `cf-ipcountry`, else a guess from Accept-Language, else Georgia). The
country picker is a GET form (`next/form`, works without JavaScript); prices
show in the country's currency, with the plan's euro price beside them when
they differ and "≈" for converted amounts. It has its own metadata for search
engines (the cabinet's pages are `noindex`) and texts in
`i18n/messages/landing/`.

## Channels and sign-in

- `/b/[businessId]/channels`: channel cards (a channel in `error` shows when it
  stopped and what the platform said), the website chat's look (colour, corner,
  a sketch and a link to the API's `/widget/demo` with the unsaved choices) and
  embed code, call forwarding, Google Calendar (connection, calendar, last sync
  and its error) and staff Telegram links. Google's consent page returns
  (through the API's public callback) to `/integrations/google-calendar/callback`,
  a route handler that finishes connecting with the owner's session (only the
  user who started can finish) and then opens `?calendar=connected` or
  `?calendar=error&reason=…`; `page.tsx` reads it, the screen shows it once and
  removes it from the address. The API needs `CABINET_BASE_URL` set to this
  cabinet's public address; without it Google Calendar cannot be connected.
- The proxy answers a plain form POST to a page (the payment page returns the
  payer that way, without the SameSite=Lax session cookie) with a 303 to the same
  address, so the browser repeats it as a GET that carries the session.
- `/login` asks `GET /v1/auth/login-options` for the chosen country: the method
  switch hides e-mail when it cannot deliver codes, the phone form offers a
  channel choice when several work, and explains when none does. The code
  screen offers the country's other channels ("No code? Send by SMS instead":
  a number without WhatsApp is reported only later), which the API allows at
  once. Phone numbers and codes typed in any script (Arabic-Indic, Persian,
  full-width digits, direction marks of copied numbers) are read as ASCII
  digits (`toAsciiDigits`). Helpers with tests are in
  `src/app/login/_lib/loginOptions.ts` and `src/lib/countries.ts`.

## Security notes

- Session: httpOnly, `SameSite=Lax`, `Secure` in production cookie `aw_session`
  holding the API bearer token; expires with the API session. A 401 from the
  API clears it.
- The BFF forwards only `/v1/*` paths, an allow-list of headers (never the
  browser's cookies), and refuses cross-site state-changing requests
  (`Origin`/`Sec-Fetch-Site` check) on top of `SameSite=Lax`.
- After sign-in the cabinet only redirects to same-site paths (`safeNextPath`).
