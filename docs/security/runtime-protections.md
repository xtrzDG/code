# At run time: what the running service refuses and limits

The gates that keep vulnerable code out are in `SECURITY.md`; the threats
these measures answer, boundary by boundary, are in
`docs/security/threat-model.md`. This page lists what the deployed API,
worker and cabinet do at the platform's edge, each with its code and the
test that proves it; the AI agent, calls, bookings, payments and
customers' data follow in `docs/security/product-protections.md`.
`tests/legal/test_operations_documents.py` fails when a path in either
moves.

## Configuration

- **Production fails closed.** With `APP_ENV=production` the API and every
  worker run `run_startup_checks` before they serve
  (`app/gateways/startup_checks.py`, rules in
  `app/utilities/config_helpers/production/`) and stop with one error that
  names every offending variable: in-memory storage, local recordings, a
  missing, public or short `ENCRYPTION_KEY`, http or loopback addresses,
  CORS `*` (refused in every environment), no or test Turnstile keys,
  `SMTP_SECURITY=none`, no login-code channel, the scripted model or a
  missing model key, Stripe test or publishable keys, Flitt's test
  merchant, an enabled feature without its webhook secret, `LOG_FORMAT=text`,
  no daily spend budget and the development seller. An unknown `APP_ENV`
  never starts, and an unset one does not start on Render. The full list
  is in `docs/operations/go-live.md` ("Production refuses to start"); the
  Blueprints are tested never to set a refused value
  (`tests/platform/test_production_requirements.py`,
  `tests/platform/test_production_startup.py`,
  `tests/platform/test_deploy_gating.py`).
- Staging runs the same checks (`APP_ENV=production`, a real model), so a
  deploy that would not start in production fails on staging first.

## Sign-in and sessions

- **Sign-in codes** are stored as an HMAC-SHA256 under a key derived from
  the `ENCRYPTION_KEYS` ring and checked against every key of the ring: a
  copy of the database alone cannot test a challenge's million codes
  offline (`app/utilities/security/one_time_codes.py`;
  `tests/users/test_login_code_hashing.py`). Codes issued before this
  release are read the old way until they expire (10 minutes).
- **Code spraying**: one client network asking codes for 10 or more
  different phones or e-mails within an hour alerts the platform admins
  (e-mail to `PLATFORM_ADMIN_EMAILS`, a warning and a Sentry event); it is
  an alert, never a refusal (`app/use_cases/users/otp_login/login_code_spray.py`,
  `app/facilitators/users/sign_in_code_spray_alert_facilitator.py`;
  `tests/users/test_login_code_spray.py`).
- **New device or country**: a person is told of a sign-in from a new
  device, or from a country none of their live sessions came from (needs
  `GEOIP_COUNTRY_DATABASE_PATH`), by their devices and, for e-mail
  sign-ins, by e-mail, in English or Italian
  (`app/facilitators/users/sign_in_notice_facilitator.py`;
  `tests/users/access/test_sign_in_country_notices.py`).
- **Step-up**: exports, erasures, team changes, deleting an account or a
  business, admin actions and every change of deposit payment pages (add,
  remove, a new default, a rule pointed at another page) need a sign-in
  within `STEP_UP_MAX_AGE_SECONDS`; otherwise 401 `step_up_required` and
  nothing is written. Owners are told of every payment-page change, with
  the hosts only (`tests/deposits/test_payment_page_step_up.py`,
  `tests/deposits/test_payment_page_rule_changes.py`).
- **Ending sessions**: "sign out everywhere", this device included
  (`POST /v1/me/sessions/revoke-all`, audited;
  `app/use_cases/users/sessions/revoke_all_sessions_use_case.py`;
  `tests/users/access/test_sign_out_everywhere.py`); a SUPER platform admin
  ends every session of a client's team member (step-up, audited on the
  platform chain; `tests/users/access/test_admin_member_sessions.py`);
  joining the platform-admin team ends a person's existing sessions, so
  admin rights come only with a new sign-in
  (`tests/users/access/test_admin_role_sessions.py`); so does a member
  made an owner of a business, and an existing account invited directly
  as an owner (it joins at once): the sweep runs before the change is
  stored and again after it, so a failed first sweep stores nothing and a
  retry sweeps again (`app/use_cases/businesses/owner_promotion_sweep.py`,
  `app/use_cases/businesses/invite_staff_use_case.py`;
  `tests/businesses/test_owner_promotion_sessions.py`,
  `tests/businesses/test_owner_invitation_sessions.py`).
- **Session rotation**: a proof that raises a one-factor session to two
  factors (a step-up, a new authenticator, a first passkey) is not written
  on that session. The session keeps only the SHA-256 hash of a one-time
  rotation ticket (256 random bits, 120 seconds, bound to that session),
  and the ticket goes in the proof's answer to the client that made it
  alone. With it the cabinet's server swaps the token
  (`POST /v1/auth/session/rotate`); taking the ticket and winding the old
  session down are one atomic write, and only the new token carries the
  two factors and the proof. The old token stays one factor with no
  proof, answers 30 seconds more for requests on their way, never takes a
  proof or a ticket again (`rotated_at`) and is left out of the device
  list. A session stored as one factor is never raised in place, even
  when it was lowered while a proof ran; a use of a session never moves
  its stored end later, so a stale read cannot undo a wind-down or an end
  (`app/use_cases/users/sessions/session_proofs.py`,
  `app/use_cases/users/sessions/rotate_session_use_case.py`,
  `app/repositories/user_session_changes.py`,
  `web/src/server/sessionRotation.ts`;
  `tests/users/access/test_session_rotation.py`,
  `tests/users/mfa/test_step_up_rotation.py`,
  `tests/storage/test_session_store_writes.py`,
  `tests/users/access/test_device_sessions.py`,
  `web/src/app/api/auth/session/rotate/route.test.ts`). Residual: a
  sweep (factor removal, owner promotion) that runs between the old
  session's wind-down and the new session's save does not see the new
  one; that token is held only by the client that made the proof.
- **Google Calendar** connects with PKCE (S256) and a state bound to the
  person and the session that started it; completing it checks again that
  the person still owns the business
  (`app/use_cases/calendar/start_google_calendar_connection_use_case.py`,
  `app/use_cases/calendar/calendar_state.py`;
  `tests/operations/test_google_calendar_pkce.py`).
- **Guest links**: a booking's manage link carries a 128-bit MAC (older
  96-bit links open until they expire;
  `app/utilities/security/booking_manage_token_signer.py`;
  `tests/bookings/test_booking_manage_tokens.py`); the booking page trades
  it for a credential of about 30 minutes and takes the token out of the
  address bar (`POST /v1/public/bookings/{token}/session`;
  `tests/bookings/test_booking_manage_session.py`). Every answer to a
  credential carries a credential that ends no later, with one exception:
  the calendar file (`…/calendar.ics`) embeds a freshly signed long-lived
  manage link, so the guest's calendar entry keeps a working link
  (`app/use_cases/bookings/public/get_managed_booking_calendar_use_case.py`).
  A website-chat visitor
  key idle for 30 days reads nothing from before the gap
  (`tests/channels/test_widget_visitor_key_expiry.py`). On the hosted chat
  page the conversation and its visitor key live in the tab's
  `sessionStorage` and leave with it; on a business's own site a
  conversation idle for a day is wiped from the device
  (`tests/channels/test_widget_storage_expiry.py`), and nothing is written
  to the site's storage until the visitor opens or uses the chat: the key
  is made on the first message, handoff, upload or rating, and an unused
  key of older versions is removed on load
  (`app/gateways/http/static/widget/storage.js`,
  `tests/channels/test_widget_lazy_storage.py`).

## The API's edge

- **Webhook admission** (`app/gateways/http/middleware/webhook_admission_middleware.py`,
  `app/gateways/http/middleware/webhook_deliveries.py`): a delivery without
  a well-formed signature header of its provider gets 401 (Stripe 403)
  before its body is read, and floods get 429 with `Retry-After`, counted
  per provider and client network in each process: 1,200 a minute for
  Telegram, Meta and the voice tools, 600 for the platform bot and the call
  start, 300 for the post-call, Zadarma, Twilio, Stripe and Flitt
  (`tests/security/test_webhook_admission.py`). Signatures themselves are
  verified as before (threat model, row 4).
- **Replays**: a Zadarma notification must be recent and a signed copy
  under another call id is ignored (`app/adapters/voice/zadarma_replay_guard.py`;
  `tests/calls/test_pbx_notification_replays.py`); Twilio's signature has
  no time, so each fallback or dial-status request is claimed once for at
  least a day and a copy rings nobody and tells nobody
  (`app/adapters/telephony/twilio_replay_guard.py`;
  `tests/calls/test_twilio_request_replays.py`); an ElevenLabs timestamp
  may be at most 5 minutes ahead of the clock
  (`app/utilities/channels/webhook_signatures.py`;
  `tests/channels/test_webhook_signatures.py`).
- **Rotating a webhook secret** refuses no callback: while the provider
  switches, the old value in `<NAME>_PREVIOUS` is accepted after the
  current one (ElevenLabs, Meta, Flitt, Zadarma, Twilio), never alone and
  never to sign anything (`app/utilities/config_helpers/secret_rotation.py`;
  `tests/platform/test_previous_secrets.py`,
  `tests/channels/test_webhook_secret_rotation.py`;
  `docs/operations/runbooks/secret-rotation.md`).
- **Anonymous limit per address**: an `Authorization` header exempts a
  request only on routes that verify a credential; a made-up one counts
  against the address
  (`app/gateways/http/middleware/anonymous_request_limit_middleware.py`;
  `tests/security/test_anonymous_limit_headers.py`).
- **Bodies**: 1 KiB on GET, HEAD and OPTIONS, 64 KiB for telephony forms,
  256 KiB by default, 1 MiB for webhooks, 5 MiB for the post-call, 21 MiB
  for a menu import, 26 MiB for a widget upload (413;
  `app/gateways/http/middleware/body_size_limit_middleware.py`); JSON nested
  deeper than 64 levels gets 422 `too_deep`, measured in linear time, and
  bodies over 64 KiB are parsed off the event loop
  (`app/gateways/http/json_nesting.py`,
  `app/gateways/http/strict_request_parsing.py`;
  `tests/security/test_api_body_limits.py`,
  `tests/security/test_json_nesting.py`,
  `tests/api_fuzz/test_hostile_bodies.py`).
- **Deadline**: a request that has not started answering within 60 s (170 s
  for model-backed and upload routes) gets 504; streams are not cut
  (`app/gateways/http/middleware/request_deadline_middleware.py`;
  `tests/security/test_request_deadline.py`).
- **Public probes**: the widget's config is cacheable for 60 s and limited
  to 120 requests a minute per client network; `/readyz` shares one check
  every 2 s and allows 60 probes a minute per public network, never
  counting private addresses (`tests/security/test_public_probe_budgets.py`).
- **Headers**: HSTS of two years with subdomains and `preload` in
  production, `Cross-Origin-Opener-Policy: same-origin`,
  `default-src 'none'; base-uri 'none'; frame-ancestors 'none'`, `nosniff`,
  `no-referrer`, `no-store` on `/v1`, no `/docs` or `/openapi.json` in
  production (`app/gateways/http/middleware/security_headers_middleware.py`;
  `tests/security/test_api_security_headers.py`). The API reads no cookies
  and its CORS never allows credentials
  (`tests/security/test_api_reads_no_cookies.py`).
- **Idempotency**: the admin's money actions (credits, discount, trial
  extension, setup-fee waiver, manual payment, plan, partner payouts), a
  deposit payment link and a deposit marked paid take an
  `Idempotency-Key` (`tests/idempotency/test_idempotency_over_the_api.py`).
- **Security log**: logger `app.security`, field `security_event`
  (`webhook_delivery_refused`, `authorization_denied`,
  `rate_limit_triggered`, `request_body_refused`,
  `request_deadline_exceeded`, `job_tenant_mismatch`) with the path
  template, the reason and the client network (/24 or /48), never an
  address, token or personal data; a 429 line at most once a minute per
  route and network (`app/utilities/observability/security_events.py`,
  `app/gateways/http/refusal_logging.py`;
  `tests/security/test_security_events.py`).

## The cabinet (BFF)

- **Cookies**: every production deployment gets `Secure` cookies and the
  `__Host-aw_session` name; `COOKIE_SECURE=false` works only for a
  production build reached over plain HTTP on the same machine, and the
  old `aw_session` is never read in production
  (`web/src/server/cookieSecurity.ts`, `web/src/server/sessionCookie.ts`;
  `web/src/server/cookieSecurity.test.ts`,
  `web/src/server/sessionCookie.test.ts`). Without `BACKEND_URL` a
  production server fails every API call instead of asking localhost
  (`web/src/server/backend.ts`; `web/src/server/backend.test.ts`).
- **CSRF**, on top of `SameSite=Lax`: a write through any BFF route needs
  `Sec-Fetch-Site: same-origin`, or, without it, the site's own `Origin`;
  anything else is 403 `forbidden_origin`, sign-in steps included. The
  audited exports refuse other sites' navigations and fetches
  (`web/src/server/sameOrigin.ts`; `web/src/server/sameOrigin.test.ts`).
  Every BFF route that reads a body has a limit
  (`web/src/server/bodyLimits.ts`).
- **Session tokens never reach page code**: the catch-all relay
  (`/api/backend/*`) answers 404 for every API route whose answer carries
  a session token (the sign-in steps and the rotation), however the path
  is encoded, before calling the API; only the dedicated routes read
  those answers and put the token into the httpOnly cookie
  (`web/src/server/sessionTokenPaths.ts`, `web/src/server/relay.ts`;
  `web/src/server/sessionTokenPaths.test.ts`).
- **Sign-out** answers `Clear-Site-Data: "cache", "cookies", "storage"`,
  and the button also empties Web Storage itself
  (`web/src/app/api/auth/logout/route.ts`,
  `web/src/components/shell/signOut.ts`;
  `web/src/app/api/auth/logout/route.test.ts`).
- **Cookie consent**: the public site's banner (never on `/c/`, `/r/`, the
  widget or the cabinet) stores the answer in the technical cookie
  `aw_consent` for 183 days; the attribution cookie `aw_attr` is set only
  after acceptance and deleted on rejection; Accept and Reject look the
  same, and closing is a rejection (`web/src/server/consentCookie.ts`;
  `web/src/server/consentCookie.test.ts`, `web/e2e/public-a11y.spec.ts`).

## Monitoring without personal data

- **Sentry**: no default PII, no local variables, no breadcrumbs, no
  request bodies; `before_send` drops request data, user, extra data and
  frame variables and masks e-mails, phone-like numbers and secrets in
  messages and log entries
  (`app/facilitators/observability/sentry_error_reporting_facilitator.py`;
  `tests/platform/test_sentry_scrubbing.py`).
- **Logs** mask e-mail addresses and `+`-prefixed phone numbers in each
  line's message (`app/utilities/observability/contact_log_masking.py`;
  `tests/platform/test_contact_log_masking.py`). Not masked: bare digit
  runs (ids, amounts, WhatsApp ids without `+`), exception tracebacks and
  structured fields.
- **Payments** are logged as structured events (`payment_order_opened`,
  `payment_state_changed`, `payment_reconciliation_mismatch`) with ids,
  provider, purpose and statuses only, never card data or amounts
  (`app/use_cases/billing/payment_state_events.py`;
  `tests/payments/test_payment_state_events.py`).

## Added in the readiness round of 2026-11-03

- **Admins hold a passkey.** With `ADMIN_PASSKEY_REQUIRED` (on in
  production, refused off there) admin endpoints and a look into a
  client's cabinet answer 403 `passkey_required` (404 for the cabinet)
  until the admin has a passkey, and an app code from an admin who has one
  is refused; admin sessions end after 15 idle minutes
  (`ADMIN_SESSION_IDLE_TIMEOUT_SECONDS`, 900)
  (`app/use_cases/authorize_support_access_use_case.py`;
  `tests/users/passkeys/test_admin_passkey_rule.py`). Sign-in code alerts
  reach the admins once per key an hour in each process
  (`app/facilitators/users/hourly_admin_alerts.py`).
- **Team access ends with the person.** Invitations to accounts that
  never signed in lapse after 7 days (`app/use_cases/shared/lapsed_invitations.py`;
  `tests/businesses/test_invitation_expiry.py`); a member removed, or
  deleting the account, revokes the API keys they made and the webhooks
  those keys subscribed (`tests/integrations/test_removed_member_keys.py`).
- **The database connection uses TLS** whenever its address is external
  (`app/utilities/config_helpers/production/database_tls_requirements.py`;
  `tests/platform/test_database_tls_requirement.py`): a dotted or IP host
  must require it, a single-label private-network host (Render's internal
  `dpg-…-a`) is exempt unless its query names another server, and the
  Blueprints set no `PGSSLMODE`.
- **Outbound calls to providers** come from one client factory with TLS
  verification, timeouts, no redirects and a cap on the unpacked answer
  (`app/clients/http/provider_http_client.py`;
  `tests/resilience/test_provider_http_clients.py`); tenant URLs are
  fetched over https only and a refusal is the security event
  `outbound_fetch_refused` (`tests/web_fetching/test_https_only_and_refusal_log.py`).
- **Log lines** lose credentials (Bearer and Basic, Stripe and webhook
  secrets, bot tokens, token query values), card numbers, security codes,
  IBANs, ID numbers, e-mails and phones in their message, traceback and
  text fields (`app/utilities/observability/log_formatting.py`;
  `tests/platform/test_log_secret_redaction.py`).
- **The widget loader** is an immutable, versioned script the snippet
  loads with Subresource Integrity (`loader_integrity`;
  `tests/channels/test_widget_script.py`).

## The assistant, calls, bookings and money

What the AI agent, the phone line, bookings, payments and customers' data
refuse and limit, each with its code and test:
[product-protections.md](product-protections.md).
