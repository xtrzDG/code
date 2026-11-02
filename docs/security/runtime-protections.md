# At run time: what the running service refuses and limits

The gates that keep vulnerable code out are in `SECURITY.md`; the threats
these measures answer, boundary by boundary, are in
`docs/security/threat-model.md`. This page lists what the deployed API,
worker and cabinet do, each with its code and the test that proves it.
`tests/legal/test_operations_documents.py` fails when a path here moves.

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
  (`tests/users/access/test_admin_role_sessions.py`). Right after a
  step-up the cabinet's server swaps the session's token for a new one
  (`POST /v1/auth/session/rotate`; the old token answers 30 seconds more
  as one factor), so a token copied before the step-up never gains its
  level (`app/use_cases/users/sessions/rotate_session_use_case.py`,
  `web/src/server/sessionRotation.ts`;
  `tests/users/access/test_session_rotation.py`,
  `web/src/app/api/auth/session/rotate/route.test.ts`).
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
  `tests/bookings/test_booking_manage_session.py`). A website-chat visitor
  key idle for 30 days reads nothing from before the gap
  (`tests/channels/test_widget_visitor_key_expiry.py`).

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
  `tests/calls/test_pbx_notification_replays.py`); an ElevenLabs timestamp
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

## The AI agent

- **Fenced values**: what customers wrote reaches the model only inside
  one-line `<customer_value>` blocks it cannot close (the contact's name,
  request details, conversation summaries, the guest's name in booking
  results); team notes are `<team_note>`, imported knowledge
  `<untrusted>`, the owner's tone and rules `<owner_text>`, which never
  override the platform's rules. A customer who types one of these tags is
  neutralised like a forged header, and customer values never count as
  trusted evidence for the reply guard
  (`app/utilities/conversations/untrusted_text.py`,
  `app/utilities/conversations/customer_text_fencing.py`,
  `app/utilities/conversations/owner_text_fencing.py`;
  `tests/brain/test_untrusted_customer_values.py`,
  `tests/assembly/test_untrusted_blocks.py`,
  `tests/security/test_owner_text_rendering.py`).
- **Typed tool inputs**: a guest's name at most 60 characters on one line
  without markup or invisible characters, a booking note 500, lead details
  1,000, a budget 100, a handoff summary 1,000; the website chat checks a
  visitor's name the same way (422) (`tests/brain/test_tool_input_limits.py`,
  `tests/channels/test_widget_contact_names.py`). Owner texts are saved only
  as one line without `< > [ ] { }` or a backtick and not starting with `#`
  (`app/schemas/typings/profiles/constrained_strings.py`).
- **Caps**: at most 5 tool calls run per model response, and the business's
  spend is checked again before every later model round
  (`app/use_cases/conversations/replies/round_limits.py`;
  `tests/brain/test_reply_round_limits.py`); per contact and 24 hours at
  most 5 leads made in conversations and 3 staff alerts for handoffs (an
  emergency always alerts; `app/utilities/conversations/contact_daily_caps.py`;
  `tests/operations/test_contact_daily_caps.py`); a conversation is
  answered for at most 150 customer messages
  (`app/use_cases/conversations/turns/turn_gate.py`;
  `tests/brain/test_conversation_length_limit.py`). Test chats count toward
  none of them.
- **Reply guard**: a reply that repeats 5 or more words in a row of a team
  note the model was shown, or links to a host the business did not
  publish (other than the platform's hosts, well-known map services and
  Stripe's and Flitt's checkout), is rewritten once, then handed to the
  team (`app/utilities/reply_guard/team_note_quotes.py`,
  `app/utilities/reply_guard/reply_links.py`;
  `tests/brain/test_reply_guard_links_and_notes.py`,
  `tests/brain/test_reply_link_vetting.py`).
- **Disclosure**: every channel says it is an AI assistant at the start, in
  every language the detector reads; the first messenger reply links the
  business's privacy notice; asked "are you a real person?", it says it is
  an AI and offers a colleague
  (`app/utilities/conversations/assistant_texts/ai_disclosure_texts.py`;
  `tests/brain/test_first_reply_disclosure.py`).
- **Emergencies and allergens**: the assistant is not an emergency
  service; it names the country's emergency number (112), which counts as
  platform evidence, and hands off as critical; allergen and diet answers
  come only from the business's data and always suggest confirming with
  the staff (`app/utilities/assembly/instruction_rule_sections.py`;
  `tests/assembly/test_safety_rules_in_instruction.py`).

## Calls

- **A caller ID is not authentication**: the voice agent learns nothing
  about the caller from it, and `list_my_bookings`, `cancel_booking` and
  `reschedule_booking` are refused on calls with advice to hand off
  (`app/utilities/channels/voice_service.py`,
  `app/use_cases/voice/authenticate_voice_tool_call_use_case.py`;
  `tests/channels/test_voice_caller_id_tools.py`). A customer's cancel or
  move needs a contact or a proven phone and is refused from a phone call;
  staff need their user (`tests/operations/test_booking_requesters.py`).
- **Agents** accept only conversations started with a signed URL made with
  the platform's key, at most 5 calls at once and 300 a day
  (`app/adapters/voice/elevenlabs_agent_config.py`;
  `tests/channels/test_voice_agent_creation.py`); a business takes no new
  call past 600 call minutes in its day, and a blocked number is refused
  at the call's start, also by the carrier fallback
  (`app/use_cases/voice/call_admission.py`;
  `tests/spend_guard/test_voice_caps.py`,
  `tests/calls/test_call_fallback_blocked.py`).
- **Toll fraud**: calls are put through only to a mobile or landline of the
  business's country or an EU state, never to premium, shared-cost,
  special-tariff, satellite or international premium numbers, checked
  when the owner saves the staff number (422) and again before every
  transfer and fallback dial
  (`app/utilities/channels/transfer_destinations.py`;
  `tests/channels/test_transfer_destinations.py`); a transfer happens only
  while the business is open and after the owner confirmed that staff were
  told (`tests/channels/test_call_transfers.py`).
- **Recording is off by default** (`app/schemas/domain/call_settings.py`):
  without it the audio is deleted after the call and the transcript is kept
  redacted; nothing of the staff part of a connected transfer is kept; every
  greeting says where the privacy notice is
  (`tests/calls/test_call_recording_settings.py`,
  `tests/calls/test_declined_recordings.py`).

## Bookings, money and data

- **Booking caps**: customers book at most 365 days ahead and 5 times a day
  per contact; anonymous bookings (website chat, phone) at most 200 a day
  per business and 10 per client network
  (`app/use_cases/bookings/booking_limits.py`;
  `tests/operations/test_booking_daily_caps.py`).
- **Platform brakes**: a SUPER admin pauses every assistant at once (step-up,
  a reason, audited), and at `PLATFORM_DAILY_SPEND_STOP_PERCENT` of the
  daily budget every assistant stops calling the model until UTC midnight:
  customer turns go to the team, calls to the forwarding number, the
  background model jobs ask no model (quality sampling and topics skip
  the run, summaries wait an hour, knowledge indexing fails and is retried,
  a website import fails), and owners' costly actions (menu
  import, autotests, alias suggestions, renting a number) get 409
  `platform_brake` (`app/utilities/spend/platform_brakes.py`,
  `app/use_cases/spend_guard/admit_owner_action_use_case.py`;
  `tests/spend_guard/test_platform_pause_reach.py`,
  `tests/quality/test_quality_sampling_brake.py`,
  `tests/spend_guard/test_platform_brakes.py`,
  `tests/spend_guard/test_platform_pause_admin.py`;
  `docs/operations/runbooks/platform-brakes.md`).
- **Queued jobs stay in their tenant**: a business-scoped job whose payload
  names another business than the job is refused, logged as
  `job_tenant_mismatch` and dead-lettered
  (`app/operators/business_scoped_pipeline_operator.py`;
  `tests/storage/test_job_tenant_isolation.py`).
- **Payment reconciliation**: every day the checkout orders of the last 7
  days are compared with Flitt's and Stripe's own status; mismatches are
  stored, logged and alerted (`payment_mismatch`)
  (`app/use_cases/billing/reconciliation/reconcile_payments_use_case.py`;
  `tests/payments/test_payment_reconciliation.py`;
  `docs/operations/runbooks/payment-mismatch.md`).
- **Erasures survive a restore**: each customer erasure is recorded in the
  backup bucket (ids and the moment only), and a daily job erases again a
  customer a restore brought back
  (`app/use_cases/compliance/record_contact_erasure_use_case.py`,
  `app/use_cases/compliance/reapply_contact_erasures_use_case.py`;
  `tests/compliance/test_contact_erasure_ledger.py`,
  `tests/storage/test_contact_erasure_ledger_on_postgres.py`).
- **Marketing consent**: invitations to come back go only to customers with
  an active consent, recorded with its wording's version, source, who and
  when; STOP, the suppression list and a block always win
  (`app/use_cases/campaigns/campaign_writer.py`,
  `app/schemas/domain/contacts.py`;
  `tests/campaigns/test_campaign_consent.py`,
  `tests/customers/test_marketing_consent_stop.py`,
  `tests/bookings/test_booking_page_consent.py`).
