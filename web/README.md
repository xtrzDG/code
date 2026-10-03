# Assistant Workshop — owner cabinet (web)

The owner cabinet of the AI front-line assistant and its public landing page:
the product, prices by country and FAQ at `/`, sign-in by phone (any country)
or e-mail, businesses, "Create an AI assistant" (a full-screen tunnel of eight
questions ending in a live assistant; see [Create an AI assistant](#create-an-ai-assistant)),
then five calm sections (Overview, Inbox, Bookings, Assistant, Settings; see
[Navigation](#navigation)) and the platform admin. It installs as an app (manifest, icons, service worker,
offline page).
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
(`Login code 123456 via … Code logging is for development only.`).

### Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKEND_URL` | `http://localhost:8000` | Base URL of the Python API, used only on the server (route handlers, proxy, Server Components). |
| `COOKIE_SECURE` | `true` in production | `false` serves the session cookie without `Secure` (a production build over plain HTTP). |
| `TRUSTED_PROXY_HOPS` | `0` | How many right-most `X-Forwarded-For` entries the cabinet's own proxies add (Render: `1`). Only those are forwarded to the API; the rest of the header comes from the browser and could be forged. `0` forwards no client address. |
| `SENTRY_DSN` | none | Sentry project of the cabinet's errors (server and browser). Empty: nothing is sent. Browser errors go through the cabinet's own `/api/monitoring` (no CSP or ad-blocker trouble; the browser never sees the DSN), at most 120 envelopes a minute per server. Events carry no request, cookies, user or breadcrumbs, and e-mails and phone numbers in error texts are masked (`src/lib/monitoring`). The browser SDK is downloaded only after the first error. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.05` | Share of server requests traced in Sentry (0 to 1). |
| `APP_RELEASE`, `RENDER_GIT_COMMIT` | none | The deployed build in error reports; Render sets `RENDER_GIT_COMMIT` itself, `APP_RELEASE` names it on other platforms. |
| `PSEUDO_LOCALE` | off | `true` serves the pseudo-locale `en-XA` (English accented, 40 % longer, in brackets) to a browser whose `aw_locale` cookie is `en-XA`; for development and the overflow test, never in production. See [Translations](#translations). |

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
| `npm run check:intl` | Fails when this Node lacks full ICU or cannot format Georgian, Russian and English (dates, plurals, relative time, lists); CI runs it before the build, and the cabinet's image before `next build` |
| `npm test` | Vitest unit tests (`src/**/*.test.ts`) |
| `npm run e2e` | Playwright end-to-end tests against the real API (see [End-to-end tests](#end-to-end-tests)) |
| `npm run gen:icons` | Draw the installed app's PNG icons (`public/icons/`, `src/app/apple-icon.png`) from `src/app/icon.svg` in Chromium; run after changing the mark and commit the files |
| `npm run measure:first-load` | After `npm run build`: the gzipped first-load JavaScript of `/` and `/login` (or the pages given) as a browser downloads it, and the size of the lazy 3D chunk (see [Motion](#motion)); `MEASURE_VERBOSE=1` lists every file |
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
  providers blanked, `SEED_DEMO_DATA=true`) with its output in
  `e2e/.artifacts/api.log`, and the cabinet with `next build && next start`.
  Each run starts with only the demo businesses; every test other than
  `e2e/live.spec.ts` signs up its own owner. `PLATFORM_ADMIN_EMAILS` names
  one platform admin (`PLATFORM_ADMIN_EMAIL` of `e2e/support/env.ts`), whom
  `e2e/encryption-keys.spec.ts` signs in once per worker.
- Sign-in codes are read from that log (`e2e/support/login-codes.ts`); the
  `account` and `owner` fixtures (`e2e/support/fixtures.ts`) sign up through
  the API and put the session cookie into the browser, so only the sign-in
  tests type codes.
- Every test fails on a browser console error or an uncaught exception;
  `consoleErrors.allow(/…/)` accepts one a test provokes on purpose.
- A business page keeps its live event stream open, so
  `waitForLoadState("networkidle")` never comes there: wait with
  `waitForNetworkQuiet(page)` (`e2e/support/network.ts`, every other request
  of the page settled).
- The browser prefers reduced motion (`contextOptions.reducedMotion`), so
  animations end at once and the landing shows its still hero; a test about
  motion opts out with `test.use({ contextOptions: { reducedMotion: "no-preference" } })`.
- Selectors are roles and labels with texts from the cabinet's own
  dictionaries (`e2e/support/messages.ts`), so rewording a text does not break
  a test. Prefer `getByRole`/`getByLabel`; avoid CSS classes.
- Scenarios that need the voice platform or Meta (a call recording, a WhatsApp chat past its
  24-hour window) answer the card's own BFF calls with `page.route`
  (`e2e/card-recordings.spec.ts`, `e2e/card-whatsapp.spec.ts`, served by
  `e2e/support/conversation-card.ts`); the widget tests run the API's
  `/widget.js` on a fake host site (`e2e/support/widget-site.ts`).
- Fixtures: `newOwner` has a business whose assistant does not exist yet (the
  cabinet shows "Create an AI assistant"; its setup is the tunnel at
  `/b/{id}/setup`); `owner` is the same with its first
  version built through the API (`createAssistant`), so the five sections are
  open.
- The cabinet's service worker is blocked (`serviceWorkers: "block"`): it
  would take requests out of reach of `page.route()`; `e2e/pwa.spec.ts` opts in.
- Scenarios: the landing page (prices of a chosen country, theme and language
  kept after a reload, signed-in users sent to their businesses, the still
  hero with reduced motion and the 3D one without, every section revealed),
  sign-in with a German number and with e-mail (and a wrong code),
  the whole "Create an AI assistant" tunnel on a desktop and on a phone, from
  sign-in to a live assistant and the cabinet (`e2e/setup-tunnel.spec.ts`, the
  launch's progress played by the test since the suite's API has no language
  model), a reload and a later visit continuing where the owner left off,
  a business in Turkey with Turkish, English and Arabic, a failed creation
  keeping every answer, the six profile steps under Hours and rules, every section and page from
  the sidebar (`e2e/navigation.spec.ts`: the open section's pages under it,
  Advanced, folding the sidebar, the user menu) and on a phone from the tab
  bar and "More" (no sideways scrolling at 390 px, 44 px targets), the setup
  invitation before the assistant exists and the cabinet after
  (`e2e/setup.spec.ts`), what staff see and owner pages explaining themselves
  (`e2e/roles.spec.ts`), old addresses redirected with their query
  (`e2e/redirects.spec.ts`), the manifest, icons, service worker and offline
  page (`e2e/pwa.spec.ts`), an axe audit of every page in both themes and on
  a phone (`e2e/a11y.spec.ts`), switching the interface language ru/ka/en
  from the user menu, the website chat demo page of the API, going back to a
  section showing its data from the cache (no skeleton, no spinner), a
  request's status changing at once on its conversation, rolling back on a
  500 and being undone (`e2e/instant.spec.ts`, the request served by
  `e2e/support/leads.ts`), the team inbox (`e2e/inbox.spec.ts`: a staff
  member opens a notification's link on a 390 px phone, replies without
  scrolling and resolves the handoff; two people take a conversation at
  once and the second is told; notes never reach the customer's chat or the
  transcript; the demo restaurant's helpers in `e2e/support/demo.ts`), a
  customer who needs a person appearing in an open tab without a reload, with
  its badge, the tab title count and a toast elsewhere (`e2e/live.spec.ts`:
  the demo restaurant's real widget API and event stream), every page in
  the pseudo-locale at 1440 and 390 px without sideways scrolling or a cut
  control (`e2e/pseudo-locale.spec.ts`; the suite starts the cabinet with
  `PSEUDO_LOCALE=true`).

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
  public/                      sw.js (the service worker: offline page, build files, push), icons/
                               (the installed app's PNG icons, `npm run gen:icons`)
  scripts/                     measure-first-load.mjs, render-app-icons.mjs
  src/
    proxy.ts                   runs before pages: sign-in redirects, current path header, language cookie;
                               the hosted chat page's lookup and policy (server/hostedChatProxy.ts)
    app/                       routes (App Router)
      layout.tsx               <html lang data-theme> from the cookies, I18nProvider, ThemeProvider,
                               MotionProvider, ToastProvider; the browser's theme-color
      globals.css              design tokens (colours of both themes, radii, shadows), `dark:` variant;
                               imports src/styles/motion.css, landing.css and shell.css
      manifest.ts              /manifest.webmanifest: the installed app (name in the interface language,
                               colours of the theme, icons); apple-icon.png for iOS home screens
      offline/                 the page the service worker shows without a connection
      c/[slug]/                the public hosted chat page and its default privacy notice (/privacy),
                               for customers: their language, system colours, src/styles/hostedChat.css
      */template.tsx           business, admin, login, businesses: each page rises in (PageTransition)
      page.tsx                 "/": the public landing page (signed-in users go to /businesses);
                               its main buttons lead to /create (signing in first)
      _landing/                its sections: Hero (+ HeroBackdrop, HeroVisual: the 3D scene or HeroFallback,
                               its still picture), Facts, Demo (a WhatsApp conversation), Steps, Features,
                               Channels, Niches, World, Pricing (+ PlanCard, CountryPicker), Faq, FinalCta,
                               header, footer; Section (heading reveal, depth glow); scene/ (the lazy
                               react-three-fiber hero: HeroScene, AssistantOrb + orbShader, ChannelBubbles,
                               SceneAtmosphere, sceneTextures, scenePalette); landingData.ts reads the
                               public catalog on the server
      robots.ts                robots.txt: only "/" is for search engines
      login/                   sign-in by phone (country picker, only the code channels that work now)
                               or e-mail, 6-digit code: LoginScreen (layout), _components/ (DestinationForm,
                               PhoneFields, CodeForm), _lib/ (useLoginFlow, useDestination, loginTexts,
                               loginOptions)
      businesses/              the list of businesses and "New assistant" (an account without one goes
                               straight to /create); a business still being set up opens its tunnel
      create/                  "Create an AI assistant" for a new business: the tunnel's first two
                               screens (components/setup/create/), then /b/{id}/setup
      b/[businessId]/          one business: layout.tsx loads it + the user and renders the frame
                               (the five sections, or "Create an AI assistant" before the assistant
                               exists); /b/{id} redirects to its overview (next.config.ts)
        setup/                 "Create an AI assistant" for an existing business: the full-screen tunnel
                               (components/setup/flow/SetupTunnel), ?step= opens a screen
        onboarding/            the old setup address: into the tunnel before the assistant exists,
                               to assistant/profile (keeping ?step=) after
        overview/              layout.tsx: the Overview frame (tabs for owners); the dashboard: the owner's
                               value hero (bookings ≈ money, after hours, staff time, average check edited
                               in place), next step, staff "Your queue today", KPI tiles with change chips
                               for a period (?period=), daily trend chart (plain SVG), package meters,
                               breakdowns
          reports/             owners: the month so far, stored monthly/weekly/daily reports (?kind=,
                               ?report= opens one from a digest's link), the owner's summaries
        inbox/                 the team inbox (see [Inbox](#inbox)): layout.tsx keeps the list (views
                               Needs a person, Requests, Mine, Unassigned, All with live counts, search
                               and filters, a sheet on phones) beside the conversation; page.tsx when
                               none is open; [conversationId]/ the phone-first conversation (folded
                               header, transcript, sticky reply box with Resolve, Call, Book, quick
                               replies after "/", assign menu, notes and details in a panel or sheet)
        bookings/              server-paged bookings by day ("show more"), manual booking with free
                               slots (whole-day mode), details, edit, move, cancel
        assistant/             layout.tsx: the Assistant frame (live or not, "Apply changes", tabs);
                               page.tsx: the test chat ("Try it", `?version=…`)
          knowledge/           items (layout.tsx: pill tabs; server-paged, filtered by the API) + questions/
                               (unanswered, server-paged), import/ (menu photo, PDF or link; discard a
                               whole batch), resources/ (bookable resources, special days)
          profile/             "Hours and rules": the six-step profile wizard (?step=…) and "what to add"
          channels/            chat channels (with the platform's last error; WhatsApp's template for
                               staff replies), website chat code and look, call forwarding, Google
                               Calendar (state, last sync), staff Telegram link
          versions/            Advanced: versions, versions/[versionId]/ (go-live checklist, autotests
                               with live progress, publish, rollback)
        settings/              layout.tsx: the Settings frame and tabs; page.tsx: business (old
                               #team-style links move to their page), team/, notifications/,
                               quick-replies/ (owners: the replies staff insert with "/", a text per
                               language, variables), billing/ (plan, trial, usage, plans of the
                               country, invoices, payment), privacy/, audit/
      admin/                   platform admin: clients (filters, sorts) and clients/[businessId]/;
                               security/ (encryption keys: the key ring and re-encryption runs)
      api/
        auth/start|verify|logout|expired   sign-in route handlers (cookie handling)
        backend/[...path]      BFF proxy: /api/backend/v1/... -> BACKEND_URL/v1/... (JSON, and audio
                               of call recordings streamed with its type and length; Range and
                               If-Range go up, Accept-Ranges and Content-Range come back; the live
                               event stream passed on chunk by chunk, src/server/eventStream.ts)
        locale                 switch the interface language (cookie + PATCH /v1/me)
    api/                       typed API access
      schema.d.ts              generated by openapi-typescript (do not edit)
      types.ts                 named types: Schema<"BookingView">, RequestBody<path, method>, aliases
      client.ts                `api`: openapi-fetch client for Client Components (via the BFF)
      queryCache.ts            the client data cache (one entry per key, read through
                               useSyncExternalStore) and `invalidate(prefix)`; queryKey.ts, querySnapshot.ts
      queryKeys.ts             every query key, by section: queryKeys.leads.list(businessId, tab, test)
      useQuery.ts              useQuery (stale-while-revalidate), prefetchQuery
      useCursorPage.ts         paged lists ({items, next_cursor}) with "show more", prefetchCursorPage
      useMutation.ts           useMutation (optimistic change, rollback, invalidation); mutations.ts
      paging.ts                page sizes, reload length, appending pages
      sectionQueries.ts        the first queries the sidebar prefetches (shared with the screens)
      events.ts                LiveEventStream: the business's event stream (SSE over fetch),
                               reconnecting with backoff and Last-Event-ID; eventStreamParser.ts
      liveEvents.ts            event names and which query keys each event invalidates;
                               liveInvalidation.ts batches them (hidden tabs catch up on return)
      catalog.ts               useCountries / useCountryProfile / useNiches / useNiche / usePlans
      errors.ts                ApiError, error codes, localized messages
      result.ts                unwrap(): data or a thrown ApiError
      auth.ts                  startLogin / verifyLogin (browser)
    server/                    server-only code
      api.ts                   getServerApi(), serverFetch(), getCurrentUser(), getBusiness()
      theme.ts                 getTheme(): the aw_theme cookie of the request
      backend.ts               BACKEND_URL, cookies, header allow-lists, CSRF check
      relay.ts                 streaming relay used by the route handlers
      eventStream.ts           the live event stream through the BFF (no time limit, no buffering)
      sessionCookie.ts         the __Host- session cookie (read, set, clear, migrate)
      contentSecurityPolicy.ts the per-page nonce and Content Security Policy (and the hosted chat's stricter one)
      hostedChat.ts            the hosted chat page's lookup (GET /v1/public/chat/{address}) and its hand-over header
      bodyLimits.ts            request body limits of the BFF (413)
    i18n/                      config.ts (locales, negotiation), translate.ts, server.ts, client.tsx
      messages/en.ts ru.ts ka.ts   shared texts (common, auth, nav, theme, errors …); English is the reference
      messages/onboarding/     the profile wizard's texts, one file per language
      messages/landing/        the landing page's texts, one file per language
      messages/sections/       section texts, spread into en/ru/ka: insights.ts (dashboard, conversations,
                               bookings, leads, handoffs), content.ts (knowledge, assistant),
                               workspace.ts (channels, billing, settings, admin), shell.ts (navigation,
                               account, setup, app); each composes one file per namespace and language
                               from its folder (insights/bookings.ru.ts)
    components/
      ui/                      the UI kit (import from "@/components/ui"): Button, ButtonLink, Input,
                               Select, Textarea, Checkbox, Radio, Field, Fieldset, Card, Table, Badge,
                               Modal, Drawer, useModalDialog, ConfirmDialog (optionally a typed
                               confirmation), InlineError, Toast (with an Undo action), EmptyState,
                               ErrorState, Skeleton kit (Skeleton, SkeletonText, SkeletonRows,
                               SkeletonCard, SkeletonCardList, SkeletonPageHeader, LoadingRegion),
                               Spinner, LoadingBlock, PageHeader, Alert
      motion/                  motion primitives (import from "@/components/motion"): MotionProvider,
                               Reveal, FadeIn, Stagger/StaggerItem, PageTransition, TiltCard/TiltLayer,
                               AnimatedNumber, AnimatedPresenceList, MagneticButton, Parallax
      icons/                   the one icon set (import from "@/components/icons"): interface, sections,
                               brands (channel marks shared with the 3D scene: lib/channelMarks.ts)
      shell/                   the frame (see Navigation): ShellFrame, Sidebar (+ SidebarNav, UserMenu,
                               AccountPanel), PhoneTopBar, PhoneTabBar, MoreSheet, SectionFrame (a
                               section's title and tabs), BusinessShell (sections, roles, badges, the
                               setup gate; the tunnel is drawn without it), setup/ (SetupEntry, SetupHero,
                               SetupStages), OwnersOnlyPage,
                               LiveEvents (the live stream, attention counts, tab title count, toast
                               and chime), LiveStatus ("Live · Updated just now"), ChimeSetting,
                               ServiceWorker (registration), useInstallPrompt,
                               AdminShell, TopBar (pages outside a business), Brand, SignOutButton
      setup/                   "Create an AI assistant" (see the section of that name): the frame
                               (TunnelFrame, TunnelBackdrop, TunnelRail, TunnelHeader, TunnelStage,
                               StepScreen, SaveTracker, useAutosave, useTunnelPlace, QrImage), create/
                               (/create), flow/ (/b/{id}/setup: SetupTunnel, the step context, saving),
                               steps/ and fields/ (the first two screens), offer/, hours/, people/,
                               channels/, try/, launch/ (useStagedApply: "Apply changes" as staged
                               progress, shared with the cabinet), finale/
      assistant/               "Apply changes" in the daily cabinet: ApplyChangesProvider (in
                               BusinessShell, owners), PendingChangesBanner over every page ("2 changes
                               are not with your customers yet · Review and apply"), ApplyChangesSheet
                               (the changes in the owner's words, the launch's stages, why it stopped
                               with the page that fixes it and the failed conversation), usePendingChanges
      theme/                   ThemeProvider (useTheme), ThemeSwitcher (dark / light / system),
                               useResolvedScheme (the scheme showing now, for the WebGL scene)
      business/                BusinessContext (useBusiness, useBusinessFormat, isSetUp), status badges,
                               pageMetadata (page titles), SectionLoading (a page's loading.tsx)
      value/                   what the assistant is worth (dashboard and Reports): valueModel (changes,
                               staff time, whole money, report periods), DeltaChip (a change in words for
                               screen readers), AverageCheckEditor (in place), useValueQueries
      insights/                shared by dashboard … handoffs: status badges and label maps, segmented
                               control, customer-message dialog, LoadMore, business-local dates, useToday (moves on at the business's
                               midnight), replaceUrlQuery, useAutoReload (lists whose every load
                               is audited pass `intervalMs: null` and reload only on return)
      content/                 shared by knowledge and assistant: SectionTabs (route tabs with a gliding
                               marker; pills inside a section frame), Tabs, Switch
      knowledge/websiteImport/ WebsiteImportPanel (import from the business's website: address, live
                               progress, what was found; `bare` for a host's card, the drafts go to
                               the host's review through `onReview`), useWebsiteImport, its form,
                               progress and outcome
      workspace/               shared by channels, billing, settings, admin: CopyButton,
                               UsageMeter, Facts, OwnerOnly notes, channel names,
                               MarkdownDocument (renders the DPA text without HTML), helpers (zoned
                               dates, usage)
      BusinessSwitcher.tsx LanguageSwitcher.tsx CountrySelect.tsx
    lib/                       pure helpers with unit tests (*.test.ts): navigation (pages, paths,
                               where a path is, safeNextPath), sections (the five sections, their pages,
                               roles, titles), legacyRoutes (old addresses), inboxBadges, shellPreferences
                               (sidebar cookie), installPrompt, serviceWorker.test.ts (public/sw.js), format (Intl, money units),
                               intl/ (Intl factories; Georgian dates, numbers, lists from CLDR tables), countries (phone/country),
                               hours (opening hours), wizard/ (niche answers, offers, FAQ), knowledge/
                               (kinds, item form, menu import, websiteImport), resources, assistant/ (versions,
                               autotests, go-live, test chat), validation (zod), classMerge (className
                               overrides), cn, theme (cookie, theme colours), landing (country guess,
                               plan prices), motion (motion tokens), motionMath (springs, tilt, count-up),
                               heroScene (3D hero: device check, orbits, camera), channelMarks, tunnel/
                               (the tunnel's steps and resume place, launch stages, the /create
                               draft, offer rows, booking choices, contacts, test questions, depth
                               and confetti math)
    styles/                    motion.css (motion tokens, keyframes, press/lift/shimmer/dialog motion),
                               landing.css (backdrop, hero entrance, the still hero picture), shell.css
                               (the phone sheet, the user menu, the setup entry's running light),
                               tunnel.css (the tunnel's rings, glow, burst and rail)
```

## Navigation

The cabinet is five places, the same on every screen size
(`src/lib/sections.ts` is the one table; the sidebar, the phone tab bar, the
section tabs, page titles and the e2e suite read it):

| Section | Pages (`/b/{id}/…`) | Who |
| --- | --- | --- |
| Overview | `overview?period=…` (dashboard), `overview/reports?kind=…&report=…` | owners; staff: the dashboard only |
| Inbox | `inbox[?view=needs_person\|requests\|mine\|unassigned\|all]` (one page, its views; `needs_person` without a query), `inbox/{conversationId}` | owners, staff |
| Bookings | `bookings` | owners, staff |
| Assistant | `assistant` ("Try it", the test chat), `assistant/knowledge[/questions\|/import\|/resources]`, `assistant/profile?step=…` ("Hours and rules"), `assistant/channels`; under Advanced `assistant/versions[/{versionId}]` | staff: "Try it" only |
| Settings | `settings` (business), `settings/team`, `settings/notifications`, `settings/quick-replies`, `settings/calls`, `settings/billing`, `settings/privacy`, `settings/audit` | owners; staff: Notifications only (their own devices, events and quiet hours) |

- **Sidebar** (large screens): the mark, the business switcher (it keeps the
  page when switching), the sections with icons and a marker that glides to
  the open one, the open section's pages under it (Advanced as a disclosure),
  and the user menu at the bottom: who is signed in, the interface language,
  the theme, "Install the app", all businesses, the platform admin, sign out
  (a native popover). The arrow folds the sidebar to a rail of icons; the
  choice lives in the `aw_sidebar` cookie, so the server draws it right.
- **Phones**: a calm top bar (the mark, the business, where you are), the
  bottom tab bar (Overview, Inbox, Bookings, Assistant, More; places of at
  least 56 px, above the home indicator) and "More", a sheet with Settings and
  its pages, the business switcher and the account panel. An open
  conversation takes the whole screen (no tab bar, the frame steps aside).
- **Section frames** (`components/shell/SectionFrame.tsx`): Assistant and
  Settings show the section's `<h1>`, what it is for and the
  tabs of its pages; a page's own `PageHeader` inside becomes an `<h2>` for
  screen readers and shows only its description and actions (`SubPages`).
- **Roles**: staff see Overview, Inbox, Bookings and the test chat; a page
  their role does not open (an old link to settings) explains itself
  (`OwnersOnlyPage`) instead of failing. Platform admins see what owners see.
- **Badges**: what waits for a person, from
  `GET /v1/businesses/{id}/attention-counts` (counts only, not audited): open
  handoffs and new requests on Inbox, upcoming bookings to
  confirm on Bookings, channels in error on Assistant → Channels (owners).
  Every live event reloads them (polled every minute only while the stream is
  down); the tab title starts with their sum ("(3) Bookings · …"). The
  overview's "open handoffs" tile reads the same counts.
- **Before the assistant exists** (`business.status` is `onboarding`): the
  sidebar holds one big "Create an AI assistant" entry, every page shows the
  invitation (`SetupHero`: the assistant's orb among its channels in a
  tilting card, a floor of light running towards the viewer, the three
  stages, progress once a step is done, one button), and the setup flow is
  the full-screen tunnel at `/b/{id}/setup` (see
  [Create an AI assistant](#create-an-ai-assistant)). Staff read that the
  owner is setting it up. "New assistant" in the business switcher and on
  the businesses page opens `/create`.
- **Old addresses** (`src/lib/legacyRoutes.ts`, 307 redirects in
  `next.config.ts`, the query kept): `dashboard` → `overview`,
  `conversations[/…]` and `messages[/…]` → `inbox[/…]`, `handoffs` and
  `messages/handoffs` → `inbox?view=needs_person`, `leads` and
  `messages/leads` → `inbox?view=requests`, `knowledge[/…]` → `assistant/knowledge[/…]`,
  `channels` → `assistant/channels`, `billing` → `settings/billing`, `/b/{id}`
  → `overview`; `settings#team` (a hash never reaches the server) is moved by
  the settings page, and `onboarding?step=…` by the old setup page: into the
  tunnel before the assistant exists, to Hours and rules after.

### What each page does

| Page | What the owner does there |
| --- | --- |
| Overview | What the assistant is worth (owners: its bookings times the average check, after-hours conversations, staff time saved, against the period before; the average check is edited in place), the next step for the business status, open handoffs and unanswered questions (staff: their queue of the day), KPI tiles with change chips, a daily trend chart with a table view, package minutes and dialogs (staff too, without prices), languages/channels/handoff reasons |
| Overview → Reports | The month so far, stored monthly reports and weekly/daily digests with every number against the period before, the owner's choice of summaries (monthly, weekly, daily) |
| Inbox | The team's one list: views Needs a person, Requests, Mine, Unassigned and All with live counts; a search and the history filters (period, status, test conversations) look through All; who handles each conversation, its notes, what waits. See [Inbox](#inbox) |
| Inbox → a conversation | Made for a phone: the transcript under a folded header (customer, channel, who handles it; the rest in Details), what waits above it (the handoff's reason and urgency, open requests with their status), a sticky reply box with Resolve, Call and Book and quick replies after "/"; the assign menu; notes and details in a side panel (a column of their own from 1536 px, a sheet below). Calls with their summary and recording (downloaded once and audited when "Play recording" is pressed), rating, linked bookings, staff reply (after the WhatsApp 24-hour window: in the owner's approved template, or a pointer to Channels), booking for the customer with the confirmation prefilled. Model, tokens, cost and tool calls stay behind "Technical details" (open by default for platform admins) |
| Bookings | Server-paged day groups with place and order filters, manual booking with free slots (whole day), edit, confirm / complete / no-show / move / cancel and the customer text |
| Assistant → Try it | Test chat with tool calls (`?version=…` talks to a chosen version); "Apply changes" opens the sheet with what customers do not get yet |
| Every page (owners) | The banner "N changes are not with your customers yet · Review and apply" while the profile, knowledge, hours, prices or booking rules differ from what customers get (`GET …/assistant/pending-changes`); its sheet lists them in the owner's words and applies them: the tunnel's three stages over `POST`/`GET …/assistant/apply` and the live event stream, a quick check of what changed, then the toast "Your assistant now knows: …"; a stop says why in plain words with the page that fixes it and the conversation that failed (`versions/{id}?checks=problems`) |
| Assistant → Knowledge | Server-paged items and search, unanswered questions to FAQ, menu import with review and batch discard, import from the business's website (queued, live progress, same review; `?source=website`), resources and special days |
| Assistant → Hours and rules | The six profile steps (niche and languages, contacts and hours, offer, booking rules, FAQ and handoff, channels), each saved on its own; the "what to add" summary opens the full list in a side panel |
| Assistant → Channels | Connect messengers and see why one stopped, WhatsApp's template for staff replies after 24 hours (name and language), website chat snippet, colour and corner, call forwarding codes, Google Calendar state and last sync, staff Telegram link |
| Assistant → Channels → Share | The hosted chat page's link (copy, open, a new address for owners: old addresses keep working) and a link per switched-on channel, tagged with where it goes (`?src=`); a QR code made in the browser (`uqr`) as PNG or SVG, and a printable A6 table card in a business language (an iframe preview printed as is) |
| Hosted chat page (`/c/{address}`) | Public, for customers: the widget in page mode, full screen on phones, in the visitor's language (Accept-Language among the business's), the business's colour; older addresses and the business id move to the current one; `noindex`, a policy that allows only the API; texts in all widget languages (`lib/hostedChat/`); `/c/{address}/privacy` is the platform's default privacy notice (ka, ru, en) |
| Assistant → Advanced | Versions (and building one by hand), go-live checklist with fix links, autotests with live progress, publish and rollback with reasons; drafts a newer live version left behind are discarded |
| Settings → Plan and billing | Trial (it starts by itself at the first go-live; the card says so until then, and the owner may start it earlier), subscribe with payment (after the trial, an overdue payment or a cancellation), plan change, usage meters, invoices, payment |
| Settings → Quick replies | Owners: the replies the team sends often, each with a name, a shortcut typed after "/" and a text per language of the business; buttons insert the variables the API fills (`{name}`, `{booking_time}`, `{business_name}`) and a preview shows how a customer reads it; a shortcut already taken or too many replies are said in the form |
| Settings → Notifications | For everyone: **On this device** (Web Push: the browser asks for permission, subscribes with the server's VAPID key and the subscription goes to the API; "Send a test" answers whether it arrived; "Turn off"; my other devices), **What reaches me** (events and quiet hours of my devices, in the business time zone). For the staff contacts: how notifications reach each one (channel without a provider on the server, the latest one delivered, waiting or failed with the reason), the linked Telegram chat's @username, and for owners "Send a test" (at most 5 per contact and hour) and each contact's events and quiet hours in its dialog |
| Notification links (`/n/{token}`) | The link at the end of every staff e-mail, SMS, chat message and device notification: signed in first (the proxy sends visitors to `/login?next=…`), then the API says where it leads (a conversation, the requests, the bookings of the booking's day, the notification settings) and the page opens there; an expired (7 days), altered or foreign link says so (`app/n/[token]/page.tsx`, `lib/notificationLinks.ts`) |
| Settings → Calls | Owners: **Call summaries** after every call (on by default; who gets them is the staff contacts in Notifications), **Text back missed callers** (off by default: the approved WhatsApp utility template's name, checked like Meta does, and the SMS fallback, with what a caller who did not get through would get now: the template, an SMS or nothing yet and why), **Template text** (the body to register with Meta in each language of the business, with Copy, and what callers read) and **Latest text-backs** (the last 20 callers who did not get through: number, when, why, Sent/Sending/Not delivered/Not sent with the reason, the channel and a link to the WhatsApp conversation their reply continues in). A conversation's calls show each summary in the reader's language |
| Settings → the rest | Business settings and pause, team with owner/staff roles, manager contacts, reading and accepting the data processing agreement, the customer list with export and erasure, the audit log with server filters. Business and Notifications save with the business `revision` they showed (`expected_revision`); when someone saved since (another owner, the Telegram bot adding a manager), the API answers 409 `stale_revision` and the page reloads and says so instead of overwriting. Business starts from the business as stored when it opens, and after a stale refusal keeps what was typed: fields nobody else changed are saved again at once, fields changed on both sides show the stored value |
| Admin (`/admin`, `/admin/clients/{id}`) | Platform admins: all clients (server filters, sorts and paging, totals), health, opening a client's cabinet |
| Admin → Metrics (`/admin/metrics`) | Platform admins (under More on phones): the founder's growth numbers from `GET /v1/admin/metrics` with the filters in the address (`?from=&to=&country=&niche=&source=`, period presets or chosen days): key numbers, the funnel as bars on one scale with both shares as text, the setup tunnel per screen, the MRR bridge (start, signed movements with their accounts, end; currencies without an official rate named), gross margin, a cohort grid that prints every share over a light accent, sources and Web Vitals (p75 with Google's rating) |
| Admin → Encryption keys (`/admin/security`) | Platform admins: how many keys `ENCRYPTION_KEYS` holds (never the keys), the latest re-encryption run (status, tokens checked, already current, sealed again, unreadable, Telegram webhooks registered again or not) with what it means, and **Re-encrypt stored tokens** after a confirmation (one run at a time; the page follows it until the worker is done). The runbook: `docs/operations/backup-restore.md` |

### Inbox

One list for the whole team (`app/b/[businessId]/inbox/`), replacing the
separate Messages, Needs a person and Requests pages (their addresses
redirect):

- **Views** (`?view=`, `lib/navigation.ts` `inboxPath`): Needs a person
  (the default, no query), Requests, Mine, Unassigned, All. The four work
  views come from `GET …/inbox` with live counts from `GET …/inbox/counts`
  (not audited, kept fresh by every live event); a search or a history
  filter (period, status, test conversations) belongs to All and is answered
  by the conversation feed `GET …/conversations` (`_lib/inboxModel.ts`
  decides). Both lists are audited reads, so they reload on a live event
  only while shown. On phones the filters are a sheet; from `lg` the list
  stays beside the open conversation.
- **A conversation** (`[conversationId]/`, `ConversationView`): a phone
  first layout. The header is folded (customer, channel, who handles it);
  the transcript fills the screen; the reply box with Resolve, Call and Book
  sticks to the bottom, so a notification's link (`/n/{token}`) leads
  straight to a reply. Details (customer, calls, bookings, requests, rating)
  and notes open in a panel: a sheet below 1536 px, a column of its own
  above.
- **Assigning** (`AssignMenu`, `_lib/useAssign.ts`): the team with avatars
  and how many waiting conversations each handles, me first. The choice
  shows at once and is sent with the `assignment_revision` the screen saw;
  when someone changed it meanwhile (409 `assignment_changed`) the card and
  the list reload and a toast says so. Staff may take or hand on a
  conversation nobody (or they) handle; a colleague's stays theirs until an
  owner moves it. Test conversations are not team work.
- **Notes** (`notes/NotesPanel.tsx`): internal to the team, on a dashed
  amber card with "Only your team sees this"; they live only in the notes
  panel, never in the transcript, and the API never sends them to the
  customer or the assistant (`e2e/inbox.spec.ts` checks the widget's poll).
- **Quick replies**: typing "/" in the reply box (or the "/" button) opens
  a picker of the business's replies, filled by the API for this
  conversation (`GET …/conversations/{id}/quick-replies`: customer's name,
  booking time, business name, in the conversation's language); a variable
  it could not fill stays in braces with a field to fill it before sending.
  Owners edit them in Settings → Quick replies.
- **Technical details**: model, tokens, cost and tool calls of an assistant
  message stay behind a "Technical details" disclosure (open by default for
  platform admins); under each message the requests to the business's data
  read as plain chips with what the assistant did (`TOOL_LABELS`).

### Create an AI assistant

One full-screen tunnel from a new business to a live assistant: one
question per screen in big type, a progress rail of eight steps (any step
can be opened from it), Enter to go on (except in a multi-line field, a
button, or a box that keeps Enter for itself: the offer table, the test
chat), Back and "Skip for now" (remembered by the API for the offer, the
channels and the test). Screens move with depth (`TunnelStage`: the next one
comes out of the distance, small and blurred; going back, the other way)
over a tunnel of rings in pure CSS 3D (`TunnelBackdrop`,
`src/styles/tunnel.css`: no WebGL, nothing per frame); with reduced motion
they only cross-fade and the rings stand still.

1. **Your business** (`/create`): the name, the kind of business as cards,
   the kind's required questions.
2. **Where you are** (`/create?step=place`): the country (from the sign-in
   phone, else the browser), city, address (required for kinds that take
   bookings), languages and time zone prefilled from the country. Continue
   creates the business and its assistant (`POST /v1/assistants`); the
   first two answers live in this browser until then (`lib/tunnel/draft.ts`),
   so a reload keeps them.
3. **What you offer** (`/b/{id}/setup?step=offer`): a name-and-price table
   prefilled with the kind's examples (saved only once priced), or an
   import from the website or a menu photo.
4. **Hours and bookings**: the kind's usual week and booking rules, a first
   bookable place, the kind's hour questions; Continue also accepts the
   kind's starter answers (who to call when, what never to promise, tone,
   ready answers) where the owner wrote nothing.
5. **Who helps**: the owner in one tap (sign-in phone by WhatsApp or SMS,
   e-mail, or Telegram through a one-time link with a QR code), or someone
   else.
6. **Where customers write**: the website chat and the business's own chat
   page (on by default), a Telegram bot in three steps, WhatsApp, Instagram
   and Messenger after launch.
7. **Try it**: a test chat with questions to tap.
8. **Launch**: what is ready (each step with "Fix"), the data processing
   agreement, the free trial, then "Apply changes" played out on screen
   (getting ready → trying test conversations → switching on, read every
   1.5 s); anything that stops it is listed with where to fix it.

The **finale**: confetti (none with reduced motion), the assistant's card,
its chat page link to copy and open, a QR code to try it from a phone, next
steps and "Open my assistant" into the cabinet. Answers save as the owner
goes (the top bar says "Saving…" / "Saved"); `?step=` keeps the screen in
the address, and `/b/{id}/setup` without it opens the first step not done
(`resumePlace` in `lib/tunnel/steps.ts`). The tunnel is owners' only; the
business frame draws it without the sidebar.

### Installable app

- `app/manifest.ts` (`/manifest.webmanifest`): the app opens on the
  businesses in its own window; name, short name and language follow the
  interface language, colours the theme; icons in `public/icons/` (192 and
  512, plain and maskable) and `app/apple-icon.png`, drawn from `icon.svg` by
  `npm run gen:icons`.
- `public/sw.js`, registered on signed-in pages of a production build
  (`components/shell/ServiceWorker.tsx`): keeps the offline page
  (`/offline`, in the language and theme of the moment, kept again when they
  change) with its build files and the icons; pages always come from the
  network and are never stored (they hold personal data), the offline page
  answers when there is none; build files (`/_next/static/`) are served from
  the cache once loaded; API calls (`/api/*`) and other sites pass straight
  through. It shows a pushed `{title, body, url, tag}` as a notification and
  opens its (same-site) url when pressed. "Enable notifications on this
  device" (`lib/webPush.ts`) subscribes through it; on a development server
  (no worker registered) it registers `/sw.js?push-only=1`, which only shows
  notifications and keeps nothing. Which device in the list is this browser
  is remembered per business in localStorage; a browser has one push
  subscription for the cabinet, so turning one business off keeps it for
  the others. `e2e/notifications.spec.ts` mocks the browser's Push API and
  starts a local push service (`e2e/support/push.ts`) that decrypts what the
  API posts (RFC 8291), so no real push service is ever called.
- "Install the app" in the user menu (and "More" on phones): the browser's
  own prompt where there is one (`beforeinstallprompt`), the Share → Add to
  Home Screen steps on iPhone and iPad, nothing once installed.
- A Content Security Policy must allow `worker-src 'self'` and
  `manifest-src 'self'` (both follow `default-src 'self'`).

### Accessibility

- `e2e/a11y.spec.ts` runs axe-core (WCAG 2.1 A and AA rules) on every page of
  a business in the dark and the light theme, on the setup invitation, every
  screen of the tunnel, `/create`, the businesses, sign-in and the offline page, and on a phone
  with the "More" sheet open; any serious or critical violation fails it.
- Landmarks: one `<h1>` per page (the section's, inside a section frame),
  the main navigation, the tab bar and the section tabs are named `<nav>`s,
  `aria-current="page"` marks where you are everywhere, badges read as "3
  waiting", folded icons keep their names, and touch targets are at least
  44 px on coarse pointers.
- What axe cannot check needs a person: a screen reader pass of the
  sidebar, the user menu popover and the "More" sheet (VoiceOver on macOS
  and iOS Safari) after changing the frame.

### Polish sweep (wave 7): before and after

What the screenshot tour of wave 6 showed, and what the cabinet does now.
Each line has a test (`e2e/` or a unit test) that fails if it comes back.

| Screen | Before | After |
| --- | --- | --- |
| Tunnel | The backdrop's rings and floor lines ran through the finale's title and the cards; on a phone the floor lines crossed every card | A veil of the page colour sits behind each screen's content (`TunnelVeil`); the floor shows from md up (`setup-tunnel.spec`, elementFromPoint) |
| Tunnel rail | The step's name was centred under the rail, not under its dot; "Saved" appearing pushed the rail | The name sits under the active dot (aligned to the end for the first and last); the save status has a slot as wide as its longest text |
| Offer step | A revisit listed saved lines newest first and brought back examples the owner had replaced or removed | Saved lines keep the order they were added; replaced and removed examples are remembered per business (`lib/tunnel/offerMemory.ts`) |
| Finale | "Connect WhatsApp and Instagram" even when they were connected | Next steps come from the setup and the channels: a skipped offer step, only the messengers still missing (`lib/tunnel/finale.ts`) |
| Tunnel, phone | The offer-source tabs were cut off; "Someone else" stayed open after adding a person | The tabs scroll with a fade; the form closes and the person shows in the list |
| Overview | A business not live yet saw "No active plan" and no way back into setup; chips showed the whole total as growth ("+1 920 GEL") against an empty period; a lone "·" started the phone's date line | "Continue setup", "Your free trial starts at launch"; "first period" chips; the dates take their own line |
| Conversation | The sticky date chip covered messages; Hebrew and Arabic names jumped to the far end of the bar; admins saw raw tool JSON open on phones; the views wrapped onto two rows | The chip stays in the flow; the name sits in a `<bdi>` at the start; technical details start closed below lg and remember each person's choice; the views are one scrolling segmented row |
| Booking dialog | Five buttons that wrapped ("Состоялась" alone on a row); "Не пришёл" and "Состоялась" before the booking started | One main action and "More"; completed and no-show wait for the start time; "Гость не пришёл" |
| Channels | The embed code broke inside `</script>`; the share address was cut to "loc…" | One sideways-scrolling code block with its Copy button; the address keeps the page's name (a middle ellipsis) |
| Settings | The SMS fallback stayed editable with text-backs off; "Send a test" worked for channels the server cannot send by | Both are disabled with the reason read out |
| Copy | "ассистент" on Share, "Сообщения → Нужен человек", "код … через почту", "Цены в валюте грузинский лари", "русский (ru)", two Georgian words for Inbox, "six steps" on the landing page, raw E.164 numbers split over two lines, "Asia/Tbilisi (UTC+04:00)" in the zone list and the bookings and notifications notes | "помощник", "Входящие → Нужен человек", "по почте / по SMS / в WhatsApp", "Валюта цен: грузинский лари (GEL)", "Русский", "შემოსული", eight steps, "+995 555 00 00 01" on one line, "Тбилиси (UTC+4)" |

## Conventions

### Adding a business page

1. Prefer a page inside one of the five sections over a new section (see
   [Navigation](#navigation)). A new page gets its folder
   (`src/app/b/[businessId]/<section>/<page>/page.tsx`), its path in
   `BUSINESS_PAGES` (`src/lib/navigation.ts`) and an entry with its label and
   roles in `SECTION_PAGES` (`src/lib/sections.ts`); the sidebar, the tabs,
   the titles and the e2e suite then pick it up. A new section also needs an
   icon in `SECTION_ICONS` (`src/components/shell/BusinessShell.tsx`) and,
   when it has several pages, a `layout.tsx` with `<SectionFrame section=…>`.
2. Keep `page.tsx` a small Server Component: metadata + one client screen.

   ```tsx
   // src/app/b/[businessId]/bookings/page.tsx
   import { pageMetadata } from "@/components/business/pageMetadata";
   import { BookingsScreen } from "./BookingsScreen";

   export const generateMetadata = pageMetadata("bookings");

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
   `Card`, `Table`, `Badge`, `EmptyState`, `ErrorState` and the skeletons from
   `@/components/ui`. While data loads, show skeletons shaped like the content
   (`<LoadingRegion label=…><SkeletonCardList /></LoadingRegion>`), not a
   spinner, and give the route a `loading.tsx` with the same shapes
   (`SectionLoading` keeps the real title). Owner-only actions: hide or disable them unless `isOwner`
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
  dialog is visible and can be dismissed. `toast.undoable(title, onUndo)`
  adds an Undo button for 5 seconds (the window runs down under the toast
  and stops while it is pointed at or focused); offer it only where the API
  has the inverse call (a lead's status), never by faking the change.
- `ConfirmDialog` asks before what cannot be undone or reaches customers;
  `confirmationText` makes the person type a word first. Cancel takes the
  focus; Enter confirms.
- Icons come from `@/components/icons` only (24×24 outline, `currentColor`).
- Motion is part of the kit (see [Motion](#motion)): buttons give a little
  and spring back, `Card interactive` and link tiles lift under the pointer
  (`motion-lift`), Modal, Drawer and the phone menu spring in and fade out
  (keeping their content while they fade), toasts rise in and make room for
  each other, skeletons shimmer and data settles in (`animate-settle`).
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
  right to left in any interface language. A name in a heading or a row
  next to an avatar goes in a `<bdi>` inside a `text-start` element: it keeps
  its own direction but stays beside the avatar.
- `ScrollRow` holds a row that may not fit (tabs, the inbox views): it never
  wraps, scrolls sideways and fades out the side with more to see.
- `OverflowMenu` ("More") keeps one main action in sight and puts the rest in
  a menu (arrow keys, Escape gives the focus back); the booking dialog uses it.
- A control that cannot be used yet says why: a disabled switch points at
  its hint (`Switch describedBy`), a button that stays focusable uses
  `aria-disabled` with `aria-describedby` on the reason.

### Calling the API

Client Components use the typed `api` client (requests go to `/api/backend/*`,
the BFF adds the token). Paths, parameters and bodies are checked against
`openapi.json`. Reads go through the cabinet's data cache, so a page opened
again shows its data at once while a fresh copy loads behind it:

```tsx
import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

const resources = useQuery(queryKeys.resources.list(business.id), () =>
  api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
);
// resources.data, .isLoading (nothing yet: show a skeleton), .isFetching, .error, .reload(), .setData()

const leads = useCursorPage(queryKeys.leads.list(business.id, tab, includeTest), ({ cursor, limit }) =>
  api.GET("/v1/businesses/{business_id}/leads", {
    params: { path: { business_id: business.id }, query: { limit: String(limit), cursor: cursor ?? undefined } },
  }),
);
// leads.items, .page (totals), .hasMore, .loadMore(), .isPlaceholder (other filters' rows while new ones load)

const setStatus = useMutation(
  (lead: Lead, status: LeadStatus) => api.PATCH(…, { body: { status } }),
  {
    optimistic: (lead, status) => queryCache.update(listKey, (list) => …), // shown at once, undone on failure
    invalidate: [queryKeys.dashboard.all(business.id)], // reloaded after it settles
    stale: [queryKeys.leads.all(business.id)], // reloaded when shown next
    errorMessages: { conflict: "leads.conflict" }, // optional context texts
  },
);
const result = await setStatus.run(lead, "won"); // failures are shown as a localized toast
```

- Keys come from `queryKeys` only (section first, then the business), so
  `invalidate(queryKeys.leads.all(businessId))` reaches every leads list of
  the business. `invalidate(prefix)` (`src/api/queryCache.ts`) is public: the
  live event stream calls it when the server reports a change.
- What the assistant knows changed? The changes not live yet
  (`usePendingChanges`) read themselves again whenever a key of the
  business, profile, knowledge, resources or billing sections is marked out
  of date (`queryCache.onInvalidate`); a save that touches none of them
  adds `invalidate: [queryKeys.assistant.pendingAll(businessId)]`.
- Data counts as fresh for 30 s (`staleMs`); `staleMs: 0` reloads on every
  mount (free slots, go-live checks). Forms that save with the revision they
  start from use `requireFresh: true`: they never start from a cached copy.
- Lists written to the audit log (conversations, bookings, leads, handoffs,
  customers) are not prefetched and, after a local change, are marked `stale`
  rather than reloaded on screen, so no view is recorded that nobody made.
  A live event reloads such a list only while it is on a visible screen (the
  person sees the change), never on a timer.
- The sidebar prefetches a section's first data on hover and focus
  (`app/b/[businessId]/_components/useSectionPrefetch.ts`, queries shared
  through `src/api/sectionQueries.ts`).
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

### Live updates

Pages update by themselves; there are no Refresh buttons. Each business tab
opens one Server-Sent Events stream, `GET /v1/businesses/{id}/events`,
through the BFF (`LiveEventsProvider` in `components/shell/LiveEvents.tsx`):

- An event names what changed by id only (`handoff.created`,
  `booking.changed`, `conversation.message` …; never customer text);
  `invalidationsFor` in `src/api/liveEvents.ts` maps it to query-key
  prefixes, and shown lists reload through their normal, audited routes.
  Changes arriving together are batched (200 ms); a hidden tab reloads when
  it is shown again, except the badge counts. A new kind of event: add it to
  `LIVE_EVENT_NAMES` and `invalidationsFor` (with a test).
- `src/api/events.ts` reconnects with growing pauses (1 s … 30 s, jitter,
  never sooner than Retry-After), at once after the API ends a stream (every
  15 minutes) or when the browser comes back online, and when no byte arrived
  for 2.5 heartbeats. The last event id goes along, so the API replays what
  was missed or answers `stream.resync` (everything shown reloads). 401, 403
  and 404 stop it.
- Where a Refresh button was, `<LiveStatus updatedAt={query.updatedAt}
  isFetching={query.isFetching} />` shows "Live · Updated just now" (amber
  "Reconnecting…" with "Try now" while the stream is down).
- A customer who needs a person (`handoff.created`) brings a toast with
  "Open" (the inbox on Needs a person) unless the inbox list is already
  open, and a short chime when the
  person turned it on (account panel; kept per device in `localStorage`, see
  `src/lib/chimePreference.ts`; the sound is unlocked by the first click).
- The BFF passes the stream on unbuffered (`no-cache, no-transform`,
  `X-Accel-Buffering: no`); a proxy in front of the cabinet must not buffer
  `text/event-stream` either.

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
as `reasonMessages` to `useMutation`); never match the English message.

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
- Dates, times, numbers and money: `src/lib/format.ts` and
  `useBusinessFormat()`, in the business time zone and currency; other
  formats in a UI language (lists, relative times, plural forms) through the
  factories of `src/lib/intl/formatters.ts`, never `new Intl.*(locale)`
  (`intlUsage.test.ts`). Chrome's Intl has no Georgian (it writes "ka" as
  American English, "8 hours ago") while the server's Node writes Georgian,
  so Georgian is formatted from our own CLDR tables (`src/lib/intl/georgian*.ts`)
  on both sides; their tests compare every pattern with Node's ICU.

Words follow the glossary (`docs/glossary.md`): "Needs a person", updates
and checks, Platform; staff never see an English system text in a Russian or
Georgian cabinet, and no sentence ends on a formatted date (a unit test).
`src/i18n/glossary.test.ts` checks the dictionaries themselves: every text
in its own script (no Cyrillic in English or Georgian, no Georgian in English
or Russian, no Russian or Georgian text made mostly of Latin words beyond
brand names), "помощник" and never "ассистент" in the Russian cabinet (the
product's name aside), and version and autotest words only on the
Assistant's advanced pages and the platform's. It replaces the screenshot
tour's text lint.

Phone numbers are shown with `formatPhone` (`src/lib/phone.ts`,
libphonenumber-js with its small "min" metadata): "+995 555 00 00 01", always
inside `dir="ltr"`. Time zones read "Тбилиси (UTC+4)" (`src/lib/timeZones.ts`):
the city from `src/lib/zoneCities.generated.ts` (the backend's CLDR exemplar
cities, written by `npm run gen:names`; browsers have no Georgian ones), the
offset in force at the moment.

**Pseudo-locale.** Russian and Georgian run 20–40 % longer than English. Start
the cabinet with `PSEUDO_LOCALE=true` and set the cookie in the browser
(`document.cookie = "aw_locale=en-XA; path=/"`): every text becomes
`[Šáṽé ẋẋ]`, accented, 40 % longer and in brackets, so a cut text (no closing
bracket), a hard-coded string (no accents) and an overflowing layout stand
out. `e2e/pseudo-locale.spec.ts` opens every page this way at 1440 and 390 px
and fails on a page that scrolls sideways or a button, tab or link whose
text does not fit. Dates and numbers stay English.

The interface language is chosen by the `aw_locale` cookie (set at sign-in from
the account language, by the language switcher, or by the proxy from
`GET /v1/me`), else the browser's `Accept-Language`, else English. The
language switcher (a native select showing each language by its own name)
is in the user menu of the cabinet (the sidebar's bottom, "More" on phones),
in the top bar of the pages outside a business and in the "New business"
dialog; it keeps the current page and re-renders it in the new language.

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
their names for screen readers and as tooltips) sits in the user menu of the
cabinet and in the top bar of the landing, sign-in and business list pages; it rewrites
the attribute, the cookie (a year) and `<meta name="theme-color">` without a
reload. `useTheme()` gives `{ theme, setTheme }`.

### Motion

The site moves with one set of tokens: subtle and quick in the cabinet,
expressive on the landing page, and still for anyone who asks for less
motion.

- **Tokens** (`src/lib/motion.ts`): durations, easings, springs (`press`,
  `snappy`, `layout`, `gentle`, `bouncy`), rise distances, stagger steps,
  tilt angles. `src/styles/motion.css` declares the same values for CSS,
  springs sampled into `linear()` easings with the duration they need
  (`ease-spring-snappy` + `duration-(--motion-spring-snappy)`);
  `src/lib/motion.test.ts` fails when the two drift (paste the new values
  from `cssMotionTokens()`).
- **Primitives** (`@/components/motion`): `Reveal` (on scroll) and `FadeIn`
  (on mount), `Stagger`/`StaggerItem`, `PageTransition` (CSS, used by the
  route templates), `TiltCard`/`TiltLayer` (3D tilt with glare and layers
  at depth; mouse only), `AnimatedNumber` (counts up when seen, rewrites the
  text node only), `AnimatedPresenceList` (items arrive and leave, the rest
  slide), `MagneticButton`, `Parallax` (depth layers drifting with the
  scroll). The animation code of `m.*` elements loads after the page
  (LazyMotion + domMax, `strict`: use `m.div`, never `motion.div`).
- **Cabinet**: page rise per route, the sidebar's active marker glides
  between sections and a thinner one between the open section's pages, which
  unfold under it (`layoutId`, one LayoutGroup per menu); the section tabs'
  underline (or pill) and the phone tab bar's pill glide too; the sidebar
  folds with a width transition; "More" rises from the bottom and the user
  menu springs up from its button (CSS, `src/styles/shell.css`); badges pop
  in; dashboard numbers count up, handoff and lead lists animate removals,
  dialogs and toasts as above.
- **Setup invitation**: the landing's still orb among its channels in a
  tilting card (`TiltCard`), aurora and the floor of light running towards
  the viewer behind it, the stages standing in perspective and rising one
  after another, a magnetic main button, and a light running around the
  sidebar's "Create an AI assistant".
- **Landing**: the hero text rises in with CSS from the first paint; the 3D
  hero (react-three-fiber, `_landing/scene/`): the assistant's orb with the
  six channels' bubbles orbiting it and sending it messages, mouse parallax,
  a camera that pulls back while the hero scrolls away. Every section
  reveals on scroll, glows drift as depth layers, steps stand like a
  corridor, plan and world cards tilt, the final card has a running edge
  light; a backdrop of aurora clouds, a floor grid running towards the
  viewer and grain.
- **Reduced motion**: MotionConfig `reducedMotion="user"` drops transforms
  and layout animations (fades stay, short); every CSS animation and
  transition ends at once (globals.css); tilt, magnetic pull and parallax
  stay still; numbers show their value; the hero keeps its still picture
  and never loads the 3D chunk. The markup is the same on the server and in
  the browser whatever the setting (no hydration mismatch); without
  scripts a `<noscript>` style shows every revealed block.
- **3D hero rules** (`HeroVisual`): everyone first sees `HeroFallback`, a
  CSS picture of the same scene in the same box (no layout shift). The
  scene loads when the browser is idle, only with WebGL, without reduced
  motion or data saver and with at least 4 cores and 4 GB of memory
  (`heroSceneMode`, `lib/heroScene.ts`), and fades in after its first
  frame. It stops drawing off screen, lowers its resolution when frames are
  slow and hands back to the picture if they stay slow, the WebGL context is
  lost or setup fails. `data-scene="static" | "3d"` on the hero tells which
  one shows. Nothing is downloaded at run time: bubble textures are drawn on
  canvases, reflections come from a generated studio environment.
- **e2e**: `playwright.config.ts` runs every test with
  `contextOptions.reducedMotion: "reduce"` (and SwiftShader for WebGL);
  `e2e/landing-motion.spec.ts` checks the still picture with reduced motion,
  the canvas without it (no layout shift) and the switch back when reduced
  motion is turned on.

Budgets, measured with `npm run build && npm run measure:first-load`
(gzipped JavaScript a first visit downloads; the 3D chunk excluded):

| Page | Before | Now | Budget |
| --- | --- | --- | --- |
| `/` (landing) | 168.7 KB | 204.9 KB (+36.2) | +40 KB |
| `/login` (any cabinet page carries the same motion code) | 272.5 KB | 293.0 KB (+20.5) | — |
| 3D chunk (three.js 0.182 + react-three-fiber + the scene), loaded later on capable devices only | — | 235.6 KB | — |

No layout shift (the e2e test asserts CLS = 0 with the scene). The scene is
one draw call per object (orb, shell, halo, six bubbles, six message
lights, three rings, 220 dust points): 60 fps on a laptop GPU; three.js
stays at 0.182 because react-three-fiber 9 still uses `THREE.Clock`, which
logs a deprecation warning from r183. `@react-three/drei` is not used: the
scene needs nothing from it (three's own RoomEnvironment and PMREM give the
reflections, the floating and billboarding are a few lines in `useFrame`).

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
`i18n/messages/landing/`. Its motion and 3D hero: see [Motion](#motion).

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

## Telemetry and attribution

- `lib/track.ts` queues reports for `POST /v1/telemetry/events` and sends
  them together (after 5 seconds, at 50, or with `keepalive` when the page
  is hidden or left); after a 429 nothing is sent until its Retry-After.
- `components/telemetry/WebVitalsReporter.tsx` (in the root layout) reports
  LCP, INP and CLS of signed-in pages only, as route templates
  (`/b/[businessId]/inbox`; `lib/vitals.ts`) with the device class by
  viewport width. The tunnel reports the screens entered and, going deeper,
  completed (`components/setup/useTunnelTelemetry.ts`).
- First touch: the proxy sets the httpOnly `aw_attr` cookie (90 days, never
  replaced) on a visitor's first landing or hosted chat page without a
  session: utm_*, `ref`, `src`, the referring host and the path
  (`lib/attribution.ts`, `server/attributionCookie.ts`). `/api/auth/verify`
  sends it as `signup_attribution` (whatever the browser put there is
  dropped), and removes the cookie after a sign-in. Values the API would
  refuse are left out, so a strange link never breaks a sign-in.

## Security notes

- Session: an httpOnly, `SameSite=Lax` cookie holding the API bearer token,
  `__Host-aw_session` over HTTPS (Secure, `Path=/`, no `Domain`: no subdomain
  or plain-HTTP page can set or shadow it) and `aw_session` when
  `COOKIE_SECURE=false`; expires with the API session. A 401 from the API
  clears it. A browser that still has the old `aw_session` keeps its session:
  it is read as a fallback and moved to the new name on the next page view
  (`src/server/sessionCookie.ts`).
- Content Security Policy (`src/server/contentSecurityPolicy.ts`, set by the
  proxy on every page view with a fresh nonce that Next.js puts on its own
  scripts): scripts only with the nonce or loaded by a trusted script
  (`'strict-dynamic'`), Cloudflare Turnstile allowed, no framing
  (`frame-ancestors 'none'`), `base-uri 'none'`, forms only to the cabinet or
  the Flitt checkout, `upgrade-insecure-requests` over HTTPS; `'unsafe-eval'`
  only under `next dev`. Zod's JIT would need eval: import `z` from
  `@/lib/zod` (jitless; ESLint refuses `"zod"`). `e2e/security.spec.ts`
  fails when any page reports a violation.
- Every answer sends `nosniff`, `X-Frame-Options: DENY`,
  `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy:
  same-origin`, and production builds HSTS (`next.config.ts`).
- The BFF refuses a request body over the API's limit with 413
  `payload_too_large` (256 KB, 21 MB for a menu import), before reading it
  when the length is declared and as soon as a streamed body grows over it
  (`src/server/bodyLimits.ts`).
- Sign-in: when the API asks for a bot check (403, reason
  `challenge_required` with the site key), the page loads Cloudflare
  Turnstile, shows "One more step" and sends the request again with the
  check's token (`src/app/login/_lib/botCheck.ts`, `useTurnstile.ts`).
- The BFF forwards only `/v1/*` paths, an allow-list of headers (never the
  browser's cookies), and refuses cross-site state-changing requests
  (`Origin`/`Sec-Fetch-Site` check) on top of `SameSite=Lax`.
- After sign-in the cabinet only redirects to same-site paths (`safeNextPath`).
