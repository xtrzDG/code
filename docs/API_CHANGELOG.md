# API changelog

Changes of the HTTP API as clients see them, newest first. Every pull
request that changes `web/openapi.json` adds an entry here (rules:
[api-versioning.md](api-versioning.md)). `Spec:` is the first 16 hex digits
of the SHA-256 of `web/openapi.json` after the change
(`sha256sum web/openapi.json | cut -c1-16`); the newest entry must name the
committed description (`tests/platform/test_api_changelog.py`).

Kinds of change: **Added**, **Changed** (additive), **Deprecated** (with
sunset date), **Removed** and **Breaking** (only with the `api-breaking`
label and a migration path).

## 2026-10-06 — SDK-ready operation names, idempotency keys, ETags

Spec: `d4bd89d5604f6613`

- **Breaking** (`api-breaking`) every `operationId` is now
  `<tag>_<route function name>` in snake_case instead of FastAPI's
  `<function>_<path>_<method>`: `GET /v1/admin/clients` is
  `admin_list_clients` (was `list_clients_v1_admin_clients_get`),
  `POST /v1/businesses/{business_id}/bookings` is
  `operations_post_booking`. Paths, methods, parameters, bodies and status
  codes are unchanged; only generated client code that names operations
  changes. The ids are unique and stable from now on: the oasdiff gate
  treats a changed operationId as an error
  (`.github/oasdiff-severity-levels.txt`).
  Migration: regenerate the client (`cd web && npm run gen:api` for the
  cabinet, which calls operations by path and needs no other change) and
  rename calls of `operations["…"]` types to the new ids; the old id is the
  route function name plus the path, so the new one is the tag plus the
  same function name.
- **Changed** the catalog routes (`/v1/catalog/*`, `/v1/phone-numbers/parse`
  and `…/call-forwarding-instructions`) carry the tag `catalog`; every
  operation has a tag now.
- **Added** an optional `Idempotency-Key` request header on
  `POST /v1/assistants`, `POST /v1/businesses/{business_id}/bookings`,
  `POST /v1/businesses/{business_id}/conversations/{conversation_id}/messages`,
  `POST /v1/businesses/{business_id}/billing/checkout` and `…/subscribe`: a
  retry with the same key and body gets the first answer again (header
  `Idempotent-Replayed: true`) instead of creating twice; the same key with
  another body is 409 `idempotency_key_reused`, a retry while the first
  request runs is 409 `in_progress`. Keys are kept 24 hours per user
  ([api-versioning.md](api-versioning.md#idempotency-keys)). Requests
  without the header behave as before.
- **Added** `ETag` on `GET` and `PATCH /v1/businesses/{business_id}` (the
  business revision, `"7"`) and an optional `If-Match` request header on the
  `PATCH`: a change whose If-Match names another revision is
  `412 Precondition Failed` with `error: conflict` and the reason
  `precondition_failed` (details: the current revision). Without `If-Match`
  nothing changes; the body's `expected_revision` still answers 409
  `stale_revision`.

## 2026-10-06 — wave 16 together: the live widget, the subscription lifecycle, data tasks, service levels, calendars

Spec: `d055b5c7ca2f4a76`

The API description with the five entries below merged together (the
website chat's live stream; cancel reasons, offers, the seasonal pause and
win-back; the post-deploy data tasks; the error budget; resource calendars
and booking systems). Each of those entries names the description of its
own change alone. One change of its own:

- **Changed** (description only) `SubscriptionStatus`: `paused` sits behind
  the closed release gate `subscription_pause` in this release, so
  `GET …/billing/lifecycle` reports the pause as `feature_off` (and
  `POST …/billing/pause` answers 409) even with
  `SUBSCRIPTION_PAUSE_ENABLED`, until the next release opens the gate.

## 2026-10-06 — the website chat's live stream

Spec: `5c058fb4b7ac5ebe`

- **Added** `GET /v1/widget/{business_id}/events?ticket=…`: the visitor's
  Server-Sent Events (`stream.ready`, `typing_started` when a worker starts
  the answer, `answer_ready` with `message_id`, `author`, `direction` and,
  only for a model reply the reply guard passed as CLEAN, `text`;
  `stream.resync`; a heartbeat every 20 s, 15 minutes per connection).
  401 for a missing, foreign or expired ticket, 404 while the website chat
  is off, 429 over the per-process stream limits.
- **Changed** `WidgetMessageAcceptedView` (the 202 of
  `POST …/messages`) and `WidgetMessagesView` (`GET …/messages`) add
  `stream_ticket` (40–120 url-safe characters, an hour long; null when
  none is issued). The visitor key still travels only in the body and the
  `X-Widget-Session-Key` header; old widgets ignore the field and poll.
- **Changed** `WidgetHandoffRequest` adds `reason` (`customer_request`, the
  default, or `no_answer`: the widget waited 90 s for an answer and hands
  the conversation to staff as a non-standard request of high urgency).
- **Changed** `GET /v1/widget/{business_id}/config`: a language with no
  ready FAQ question gets up to three of the niche's ready questions
  (en, ru, ka) in `starter_questions`, never one in another language.

## 2026-10-06 — subscription lifecycle: cancel reasons, save offers, seasonal pause, win-back

Spec: `6765ca8037bdcb78`

- **Changed** `POST /v1/businesses/{business_id}/billing/cancel` takes an
  optional body `CancelSubscriptionRequest` (`reason` — one of
  `CancellationReason`, `details` up to 1000 characters, `declined_offer`
  — the offer the owner said no to). Without a body it cancels as before.
- **Added** `GET …/billing/lifecycle` (owners): `offers` — the save offer
  for every cancellation reason (`pause`, `downgrade` with the cheaper
  plan, or a one-time `credit` on the next invoice, at most once per
  business), and `pause` — whether a seasonal pause is possible now
  (`unavailable_reason` otherwise), how many months, the month price,
  `starts_at` and `ends_at` (the end of a pause of each length).
- **Added** `POST …/billing/pause` (`months` 1–4, at most 4 months in any
  12; 409 otherwise), `POST …/billing/resume` (calls a scheduled pause off
  or ends a running one early) and `POST …/billing/offers/accept`
  (`reason`, `kind`, `pause_months` for a pause). Owners only.
- **Changed** (additive) `SubscriptionStatus` gains `paused`;
  `SubscriptionView` gains `pause_starts_at` and `pause_until`;
  `BillingNoticeKind` gains `pause_started` and `pause_ended`. `paused` is
  only written with `SUBSCRIPTION_PAUSE_ENABLED`, so a client that does
  not know it never meets it before it is turned on.
- **Changed** (additive) `AdminMetricsView` gains `churn`: cancellations by
  reason, offers made and accepted, pauses, win-back messages sent and
  returns after them, the newest owner comments.

## 2026-10-06 — post-deploy data tasks

Spec: `d71f85e1a8235db5`

- **Added** `GET /v1/admin/system/data-tasks` (platform admins): every
  post-deploy data task (a collection's document migration or a lookup
  column's backfill) with its status, progress, failures and
  `is_stalled`; the batch size, whether the release overlap is over
  (`rollout`) and the open, failed and stalled counts.
- **Added** `POST /v1/admin/system/data-tasks/{task_key}/retry` walks a
  failed task again (audited; 409 unless the task failed, 404 for an
  unknown key).
- **Added** `checks.data_tasks` in `GET /readyz` (`status`, `open`,
  `failed`, `stalled`); it never makes an instance not ready.
- **Added** `is_indexing` on the customers page and the knowledge items
  page: a column the list reads is still being filled after a deploy, so
  the list may be incomplete for a while.

## 2026-10-06 — service levels and the error budget

Spec: `261b9dca1f9aeb29`

- **Added** `GET /v1/admin/system/error-budget` (platform admins with the
  operations view): `ErrorBudgetView` with each ratio SLO of the last 28
  days of hourly rows (`objectives`: `series` `inbound_answered` or
  `api_availability`, `objective`, `events`, `good_events`,
  `budget_left_permille` from 1000 down to below 0, and
  `burn_rate_last_hour_percent`, 100 being the pace that spends the
  budget in exactly 28 days), the answer latency objective (`latency`:
  `target_ms`, `last_hour_p95_ms`, `hours_over_target`, `measured_hours`)
  and the rows' span (`measured_since`, `measured_until`; null before the
  first row).
- **Changed** `PlatformAlertCode` (system page alerts) gains
  `answer_budget_fast_burn`, `answer_budget_slow_burn`,
  `api_budget_fast_burn` and `api_budget_slow_burn`.

## 2026-10-06 — two-way availability: calendars and booking systems per resource

Spec: `d5d9a886a9e8990e`

- **Added** `GET /v1/businesses/{business_id}/resources/{resource_id}/calendar`
  (`ResourceCalendarView`): the linked Google calendar, the iCal feeds
  imported (host only, never the address), the booking system (Cal.com),
  the iCal export, each source's `status` (`BusySourceStatusView`: last
  attempt, last success, block count, `problem` from
  `CalendarSyncProblem`) and the next busy times (`BusyTimeView`, at most
  20). `POST …/calendar/sync` reads every source now and returns the view.
- **Added** owner-only changes: `PUT`/`DELETE …/calendar/google`
  (`calendar_id` from `GET …/integrations/google-calendar/calendars`,
  `GoogleCalendarList`, or `primary`); `POST …/calendar/ical-imports`
  (201; `url` https, http or webcal; refused addresses are 422
  `address_refused`, a sixth feed `feed_limit`, the same feed twice
  `feed_already_imported`); `DELETE …/calendar/ical-imports/{feed_id}`;
  `PUT`/`DELETE …/calendar/booking-system` (`kind` `cal_com`,
  `external_resource_id` the event type, `api_key`; a key Cal.com refuses
  is 422 with the `CalendarSyncProblem` code); `POST`/`DELETE
  …/calendar/ical-export` (`IcalExportCreated`: the feed `url`, shown once
  — the platform keeps only its hash — and the calendar view).
- **Added** `GET …/integrations` (owners, `IntegrationList`): Google
  Calendar, iCal import, iCal export and Cal.com with their
  `IntegrationState` (`off`, `on`, `attention`, `unavailable`) and how many
  resources use each, plus `resources` (`ResourceSyncSummary`: per resource
  with a calendar, its source and problem counts, last read and whether its
  bookings are shared) for the resources list's one-line summaries.
- **Added** `GET /v1/public/ical/{token}.ics` (no sign-in): the resource's
  busy times as an iCal feed (bookings and Google or Cal.com busy times,
  never imported iCal events, no guest data; `no-store`, `noindex`; rate
  limited per network and platform-wide; an unknown token is 404).
- **Changed** availability, booking, rescheduling and manual bookings treat
  a resource's busy times from its calendars as taken (no new fields).

## 2026-10-06 — wave 15 together: worker resilience, referrals and partners, the waitlist and return visits

Spec: `ce734ea095df4aa1`

No change of its own: the API description with the three entries below
merged together (why a dead job died and which job holds a customer's
message; invitations, the partner portal, payouts and "Powered by"; the
waitlist, return-visit campaigns and their growth lines in value and
reports). Each of those entries names the description of its own change
alone.

## 2026-10-06 — waitlist and return visits

Spec: `aa18f1931b37ab6f`

- **Added** `GET /v1/businesses/{business_id}/waitlist` (`filter`:
  `active`, `booked` or `ended`; paged, audited as a view) with
  `WaitlistEntryView` rows (the wish, the place held with `offer`, how the
  entry ended) and the business `timezone`; `DELETE …/waitlist/{entry_id}`
  (204) takes a waiting or offered customer off the list (any member).
- **Added** `GET`/`PUT …/waitlist-settings` (`is_enabled`, `hold_minutes`
  15–120; the counts by status). `PUT` is for owners.
- **Added** `GET`/`PUT …/campaign-settings` (owners change it): the
  opt-in return-visit message (`rule_kind` `rebook`, `recall` or
  `pre_arrival`, `delay_days`, `audience` with `segment_id`,
  `monthly_cap`), the niche's usual rule, the month so far, the last 30
  days by status and a preview per business language;
  `GET …/campaign-messages` (owners, paged, audited) lists the latest
  messages with who booked again.
- **Changed** `ValueTotals` (the value model and stored reports) adds
  `waitlist_booking_count`, `waitlist_value_minor`,
  `campaign_booking_count` and `campaign_value_minor`: the kept bookings
  the waitlist filled and those a return-visit message brought back.
- **Changed** `BookingDocument` adds `origin` (`waitlist` or `campaign`,
  null for every other booking); `AvailabilityResult` adds `is_waitlist_open`;
  `AssistantToolName` adds `join_waitlist`; `ContactRecords` (a
  customer's export) adds `waitlist_entries` and `campaign_messages`.
- **Changed** the live event stream adds `waitlist.changed` (ids of the
  entries that moved on).

## 2026-10-06 — referrals and partners: invitations, the partner portal, payouts, "Powered by"

Spec: `03dea2c61e45c3e9`

- **Added** `GET /v1/businesses/{business_id}/referrals` (owners): the
  business's own invitation code and link (`?ref=…&src=invite`), how many
  businesses signed up by it, paid and earned both sides their month of
  credit, `bookings_made` and `is_invite_card_due` (from the tenth
  booking), and `powered_by` (`is_shown`, `is_removable` on Plus,
  `is_hidden`, `url`).
- **Added** `PUT /v1/businesses/{business_id}/referrals/powered-by`
  (owners; `{"is_hidden": true}` only on Plus, else 409 `plan_required`).
- **Added** `GET /v1/partner`, `GET /v1/partner/referrals` and
  `GET /v1/partner/commissions` (keyset pages): a partner's codes and
  links, totals, the businesses their links brought and the commission of
  each paid invoice; 404 for anyone who is not a partner.
- **Added** `GET` and `POST /v1/admin/partners`,
  `PATCH /v1/admin/partners/{partner_id}`,
  `POST /v1/admin/partners/{partner_id}/codes` (409 `code_taken`),
  `GET /v1/admin/partners/payouts?month=YYYY-MM` and
  `POST /v1/admin/partners/{partner_id}/payouts` (mark a month paid;
  409 when nothing is due).
- **Changed** `GET /v1/me` adds `is_partner`; the widget config, the
  hosted chat config and the share links add `powered_by_url` (null when a
  Plus owner hid it); the admin metrics' source rows add `referral_code`
  (sign-ups split by the `ref` code); the team role `agency` is accepted
  by invitations and role changes (staff's work and building the
  assistant; never billing, the team or exports).

## 2026-10-06 — worker resilience: why a dead job died

Spec: `95672ccce196feb2`

- **Changed** `GET /v1/admin/jobs` items (`QueuedJobView`, also in the
  answers of `…/retry` and `…/discard`) add `dead_reason`
  (`attempts_exhausted`, `process_died` or `no_handler`; null for a job
  that is not dead or died before reasons were recorded). A job whose
  attempts ended with their worker process twice in a row is now DEAD
  with `process_died` instead of being tried again.
- **Changed** the inbox events of a customer's records (`ContactRecords`)
  add `holder_job_id`: the queued job that last took the message (null
  before this change). A later attempt of that job takes the message over
  as soon as the job's lease ends, so a customer whose worker died is
  answered within moments of the lease, not after the inbox's own lease.

## 2026-10-05 — wave 14 together: customers and search, booking confirmations, the spend guard, admin actions

Spec: `81926dbacb20deff`

No change of its own: the API description with the four entries below
merged together (customer cards, the staff-safe list, blocking, segments
and search; the guest's booking page and the hosted page's hours and
address; spend limits, allowed chat websites and request limits; the
admin's account actions, client notes and timeline and the business-level
metrics). Each of those entries names the description of its own change
alone.

## 2026-10-05 — customers: cards, staff-safe list, blocking, segments, search

Spec: `6c1658cd0245ac54`

- **Changed** `GET /v1/businesses/{business_id}/contacts` is open to staff:
  their rows carry `phone_number: null`, `masked_phone_number` and
  `is_phone_masked: true` until the owner allows phones
  (`staff_sees_phone_numbers`). New filters `tag` and `filter` (`vip`,
  `blocked`); rows add `tags`, `is_vip`, `is_blocked`.
- **Changed** `GET /v1/businesses/{business_id}/contacts/{contact_id}` is
  open to staff (phones masked the same way) and adds `standing`,
  `visit_count`, `last_visit_at`, `blocked_at` and `timeline`
  (conversations, bookings, leads and calls, newest first).
- **Added** `PATCH …/contacts/{contact_id}/card` (tags, VIP; owner and
  staff), `PUT …/contacts/{contact_id}/blocking` (owner only: a blocked
  customer gets no assistant reply and no reminder, text-back or feedback
  request), `GET …/contacts/{contact_id}/standing` (the conversation
  header's "Regular customer · 4 visits").
- **Added** `GET·PUT /v1/businesses/{business_id}/customer-settings`
  (`staff_sees_phone_numbers`, `known_tags`).
- **Added** saved segments, owner only: `GET·POST …/customer-segments`,
  `POST …/customer-segments/preview`, `PUT·DELETE
  …/customer-segments/{segment_id}`, `GET
  …/customer-segments/{segment_id}/members` (pages) and `GET
  …/customer-segments/{segment_id}/export` (CSV, a recent sign-in).
- **Added** `GET /v1/businesses/{business_id}/search?q=`: customers,
  conversations and bookings, up to five of each.

## 2026-10-05 — booking confirmations, the guest's booking page, the hosted page as a link in bio

Spec: `d7662b3200ec3235`

- **Added** `GET /v1/public/bookings/{token}` (public: the signed token of
  the guest's manage link is the key): the booking as its page shows it, in
  the business's time zone, without contact details of the guest
  (`ManagedBookingView`: business, status, local date and time, party,
  service, address with `maps_url`, the business's public phone,
  cancellation policy, the guest's `language`, `chat_links` to write to
  the business, `can_cancel`, `can_reschedule`, `is_over`).
- **Added** `GET /v1/public/bookings/{token}/calendar.ics` (the booking as
  an iCalendar file, `text/calendar`), `GET .../slots?date=` (free times of
  a day to move it to, `ManagedBookingSlots`), `POST .../cancel` and
  `POST .../reschedule` (`{"date", "time"}`; the answer carries the moved
  booking's new `token`). A forged, expired or outdated link is 404 with
  reason `link_invalid`, `link_expired` or `booking_changed`; a booking that
  can no longer change is 409 (`not_active`, `already_started`, or a
  booking refusal such as `taken`); limits per link, network and platform
  answer 429 with `Retry-After`. Responses are `Cache-Control: no-store`,
  `X-Robots-Tag: noindex`, `Referrer-Policy: no-referrer`.
- **Changed** `HostedChatView` (`GET /v1/public/chat/{slug}`) adds
  `timezone`, `hours`, optional `address` and `maps_url`, `takes_bookings`
  and optional `booking_url` (the business's own booking page).
- **Changed** `GET /v1/widget/{business_id}/messages` also lists the
  platform's messages to the visitor (`author: system`): a booking's
  written confirmation with its manage link.

## 2026-10-05 — spend guard: daily spend limits, allowed websites, generic request limits

Spec: `6a1f5ebeb3c3ff1a`

- **Added** `GET·PUT /v1/businesses/{business_id}/channels/web/allowed-origins`
  (team members read, the owner changes): the websites (scheme, host and
  port, no path; at most 20) that may show the business's website chat.
  `WidgetAllowedOriginsView` has `origins`, `is_restricted` and
  `always_allowed` (the hosted chat page and the cabinet's preview). An
  empty list lets any website show the chat, as before.
- **Changed** `/v1/widget/{business_id}/*` (and the hosted page's
  handoff) answers 403 `access_denied` to a request whose page (`Origin`,
  else `Referer`) is not one of the business's allowed websites, once the
  business lists any. Requests without either header, the hosted chat page
  and the cabinet's preview are never refused.
- **Added** `GET /v1/admin/spend` (platform admin): the platform's provider
  spend of the current UTC day by provider, the daily mean of the 7 days
  before, the daily budget and how much of it is used, and the clients that
  passed a spend limit today (`PlatformSpendView`).
- **Added** `PUT /v1/admin/clients/{business_id}/spend-limits` (platform
  admin, operations): a client's own daily soft and hard spend limits in
  micro-USD; `null` returns a limit to the plan's default.
- **Changed** every signed-in request counts against generic limits
  (`API_REQUESTS_PER_USER_PER_MINUTE`, default 600 a minute per person;
  exports `API_EXPORTS_PER_USER_PER_MINUTE`, default 30), and requests
  without a valid token against `API_REQUESTS_PER_IP_PER_MINUTE` (default
  120 a minute per address; the website chat, webhooks, the landing demos
  and health checks have limits of their own). Past a limit: 429
  `rate_limited` with `Retry-After`.
- **Changed** the owner's test chat (30 messages a minute per person),
  menu import (10 an hour per business) and autotest runs (one running and
  20 a day per business) answer 429 `rate_limited` with `Retry-After` past
  their limits.

## 2026-10-05 — an admin that can act, metrics that count every business

Spec: `e25d82440174a235`

- **Added** account actions on a client, each with a required `reason`
  (8–300 characters) and an `ADMIN_*` audit entry, for admins whose role
  manages client billing (SUPER, BILLING; others get 403):
  `POST /v1/admin/clients/{business_id}/trial-extension` (`days` 1–60),
  `…/discount` (`percent`, `last_day`), `…/credits` (`amount_minor`),
  `…/setup-fee-waiver`, `…/invoices/{invoice_id}/manual-payment`
  (`method` `bank_transfer` or `cash`, `reference`) and `…/plan`
  (`plan_key`, optional `billing_period`); each answers
  `AdminActionReceipt`.
- **Added** the team's notes about a client:
  `GET·POST /v1/admin/clients/{business_id}/notes`,
  `PATCH·DELETE …/notes/{note_id}` (`DELETE` answers 204), pinned first;
  `GET …/timeline?limit=&cursor=` (`ClientTimelinePage`, newest first:
  audit entries, bills and credit, subscription steps, health changes,
  setup milestones, the done-for-you request); and
  `POST …/onboarding-request/done`.
- **Changed** `ClientHealthView` adds optional `account`
  (`ClientAccountView`: trial end, discount, credit left, setup fee
  waived); `AdminInvoiceView` adds optional `number` and
  `manual_payment_method`; `AdminClientSummary.setup_option` is
  `self_serve` for a paying trial with no option chosen, as the owner sees
  it.
- **Changed** `GET /v1/admin/metrics` takes `include_admins`; `GrowthView`
  adds `businesses` (`BusinessGrowthView`: businesses created in the
  period, those of returning owners, their funnel and tunnel),
  `are_platform_admins_included`, `excluded_platform_admins` and
  `excluded_admin_businesses`; `MrrView` adds `rates` (the rates MRR was
  converted with, with their source and day).
- **Added** `AuditAction` values `admin_trial_extended`,
  `admin_discount_given`, `admin_credit_granted`, `admin_setup_fee_waived`,
  `admin_invoice_marked_paid`, `admin_plan_overridden` (in the owner's
  audit log as well; the admin's reason shows only on the admin's
  timeline).

## 2026-10-05 — wave 13 together: day 0, one story for updates, the landing page, trust fixes

Spec: `f6fb07c0d144fbd5`

No change of its own: the API description with the four entries below
merged together (periods since launch, the free trial and topics in the
cabinet's language; owner checks pending, drafts, named failures and
"Check now"; live landing-page demos, legal pages and honest prices;
one-time export links, DPA versions and the quality sampling switch). Each
of those entries names the description of its own change alone.

## 2026-10-05 — day 0: periods since launch, the free trial, topics per language

Spec: `b31a87dcb4422f75`

- **Changed** `GET /v1/businesses/{business_id}/value` and
  `GET /v1/businesses/{business_id}/dashboard` never start a period before
  the business went live (or was created): asked from earlier, `date_from`
  is that day and the new `is_since_launch` is true (the period before is
  as many days before it). `ValueModel` adds optional `went_live_at`.
- **Changed** `ValueModel` adds optional `is_trial`, `trial_ends_at` and
  `plan_cost_after_trial_minor` (the monthly price after the free trial,
  owners only). During the trial `plan_cost_minor` and `return_multiple`
  are null; `return_multiple` is also null for an estimate of nothing (or
  one that rounds to 0.0).
- **Changed** `GET /v1/businesses/{business_id}/value/topics` takes
  `?language=` (the cabinet's; else the owner's) and labels every topic in
  it; `ConversationTopicView` adds `kind` (`named` or `other`, the
  catch-all of other questions, which clients name in their own words).

## 2026-10-05 — one story for updates: owner checks pending, named failures, drafts, "Check now"

Spec: `84a15085e6d9e6ed`

- **Added** `POST /v1/businesses/{business_id}/autotest-cases/{case_id}/check`
  (owners): "Check now" asks the check once of the version customers talk
  to through the autotests' scenario runner and answers
  `OwnerCheckOutcomeView` — what it asked, `outcome`, `check_codes`, the
  `reason` in plain words of `?language=` (the owner's language by
  default; null when it passed), the semantic judge's `judge_notes`, the
  assistant's first `answer`, the test `conversation_id` and
  `answer_message_id` ("Fix this answer" opens them), the version and
  `checked_at`. 30 an hour per business (429 with `Retry-After`); 409 when
  nothing is live yet. A paused check can be asked too.
- **Added** `DELETE /v1/businesses/{business_id}/assistant/drafts/{version_id}`
  (owners, 204): discard a version built after the live one that customers
  never got; 409 for the live version, an archived one, one under test or
  one an apply is working on. Audited; the test chat no longer picks it
  and an apply never publishes it.
- **Changed** `PendingChangesView` adds `owner_checks`
  (`PendingOwnerCheckView`: the check, `added` or `changed`, its question,
  expectation, expected text and language): the owner's checks the live
  version was not checked against, which the next "Apply changes" asks
  first; `count` and `has_unapplied_changes` include them. They come in a
  field of their own, so `changes` never carries the new area value
  `owner_checks` and older cabinets list nothing they cannot name. It also
  adds `drafts` (`PendingDraftView`: version, number, status, built at).
  `PendingChange` adds optional `autotest_case_id`; `PendingChangeArea`
  gains `owner_checks` (internal to the server's comparison).
- **Changed** `ApplyAttentionView` adds `failed_checks`
  (`OwnerCheckOutcomeView`, as above) on `checks_failed`: the owner's
  checks the update did not pass, each with its question and why.
- **Changed** `AutotestScenarioResultView` adds optional `owner_check`
  (`OwnerCheckAskedView`: question, expectation, expected text as the run
  asked them), `conversation_id` and `answer_message_id`.
- **Changed** `AutotestCaseResultView` adds optional `conversation_id` and
  `answer_message_id` (the test answer "Fix this answer" opens).
- **Changed** `AutotestCaseView` adds optional `last_probe` (the latest
  "Check now" while the check is asked the same way), and `GET
  .../autotest-cases` takes `?language=` for its reasons. A new check
  without `language` takes the language its question is written in (the
  business's default when the question tells too little).

## 2026-10-05 — the landing page: live demos, legal pages, honest prices

Spec: `d10b9d16b4ccb880`

- **Added** `GET /v1/public-demos?language=` (no token): the landing
  page's demo businesses (`PUBLIC_DEMO_BUSINESS_IDS`) with their name,
  niche (named in the language asked for), city, country, languages and up
  to three starter questions per language, and how many messages one
  visitor may send each demo in an hour. A configured business without a
  published assistant is left out.
- **Added** `POST /v1/public-demos/{business_id}/messages` (no token):
  body `{"text", "session_key"}`; the demo assistant's sandbox answer
  (`text`, `language`, `is_booking_made`, `is_request_made`,
  `is_handoff_made`, `messages_left`). Any other business is 404; limits
  per conversation, network, demo and the whole site answer 429 with
  `Retry-After`; two demo turns at a time per API process.
- **Added** `GET /v1/legal/overview` (no token): `is_draft`
  (`LEGAL_TEXTS_FINAL` off), the DPA version in force and the operator's
  details (`SELLER_*`) for the public legal and contact pages.
- **Changed** `LegalDocumentKind` gains `security` (the public security
  overview, `GET /v1/legal/security`), and `LegalDocumentView` adds
  `is_draft` (true while the text has open fields or `LEGAL_TEXTS_FINAL` is
  off). Clients that map the enum must accept the new value.
- **Changed** `CountryListItem` adds `has_price_book`: every plan is billed
  in the country's own currency (the lari price book, the euro area), so
  nothing shown there is a conversion.
- **Changed** `NicheSummaryView` adds optional `typical_check` (EUR; the
  catalog list only): what one booking of the niche typically brings, the
  landing page's value calculator starts from it.

## 2026-10-05 — trust fixes: one-time export links, DPA versions, quality sampling switch

Spec: `b33cec1ddae27e18`

- **Added** `POST /v1/businesses/{business_id}/business-exports/{export_id}/download-link`
  (owners, after a recent sign-in or step-up: 401 `step_up_required`): a
  one-time `download_path` and its `expires_at` (`EXPORT_DOWNLOAD_LINK_MINUTES`,
  10 at most). 404 when the export is not ready or its archive is gone, 409
  when it was downloaded three times.
- **Breaking** (security; the cabinet changes in the same pull request)
  `GET /v1/business-exports/{business_id}/{export_id}/download?token=` now
  needs the session (`Authorization`) of the owner who asked for the link,
  and a token opens once. Signed links issued before the deploy stop
  working; owners ask for a new link from Settings → Privacy.
- **Deprecated** `BusinessExportView.download_path`: always null; sunset
  2027-04-05. Use the new route. **Added** `BusinessExportView.downloads_left`
  (of 3).
- **Changed** `DpaStatusView` adds `needs_reacceptance` and
  `acceptance_due_on` (30 days after the version's date): owners who
  accepted an earlier DPA version accept the new one (2026-10-06).
- **Changed** `PrivacySettingsRequest` / `PrivacySettingsView` add
  `quality_sampling_allowed` (default true): the nightly quality sample of
  the business's real conversations can be turned off.
- **Changed** `StaffLinkTarget` gains `privacy` (Settings → Privacy, the
  notice of an export download). Clients that map this enum must accept it.

## 2026-10-05 — wave 12 together: deeper checks, customer memory, online migrations, retention, legal texts

Spec: `0ccf13ff93342e14`

No change of its own: the API description with the five entries below
merged together (pass^k, attack scenarios, the comparison with the live
version and the quality of real conversations; the customer memory's
settings and `list_my_bookings`; the customer and knowledge lists paged in
the database and the admin client list from stored standings; retention
periods and the erasure at sub-processors; legal texts, the sub-processor
list and terms acceptance). Each of those entries names the description of
its own change alone.

## 2026-10-05 — trustworthy checks: pass^k, attacks, version comparison, production quality

Spec: `705d0e6d7f63f2a1`

- **Changed** `AutotestScenarioKind` gains the attack kinds
  `prompt_injection_spoof`, `data_exfiltration`, `staff_impersonation` and
  `tool_abuse` (planned for every niche) and `AutotestCheckCode` gains
  `price_not_named`, `unsupported_price`, `instructions_revealed`,
  `personal_data_revealed`, `unauthorized_action` and `tools_misused`.
  Clients that map these enums must accept the new values.
- **Changed** `AutotestScenarioResultView` adds optional `sample_count` and
  `passed_sample_count`: a launch-critical scenario is played
  `AUTOTEST_CRITICAL_SAMPLES` times (pass^k) and passes only when every play
  passed; the result shown is the first play that did not pass, else the
  last one.
- **Changed** `AutotestRunView` adds optional `comparison`
  (`AutotestRunComparisonView`): for a finished run of a version that was
  not live when the run started, the live version's run
  (`baseline_run_id`, `baseline_version_number`), the scenarios both runs
  played, `new_failures` and `fixed` (scenario key, kind, language, both
  outcomes, check codes), `score_changes` per scenario that moved by half
  a point or more (worst first), `criterion_changes` with every judge
  criterion's average over those scenarios in both runs, and the average
  score of both runs.
- **Added** `GET /v1/admin/clients/{business_id}/quality` (platform admins
  who view clients): `ClientQualityView`, the judge's scores of the
  client's real conversations from the nightly sample — 30 local days
  (`days`: day start, count, average), the last 7 days against the 7
  before (`drop_percent`, `is_dropping`), and the five lowest-scored
  conversations (scores only, no text).
- **Added** `GET /v1/businesses/{business_id}/conversations/{conversation_id}/quality`
  (members): `ConversationQualityView`; `score` is null unless the nightly
  sample judged the conversation, else its average, the five criteria,
  the judge's notes in the owner's language and when it was judged.

## 2026-10-05 — customer memory: Settings → General's switch, list_my_bookings

Spec: `b7d01d5dad47dd36`

- **Added** `GET /v1/businesses/{business_id}/assistant-settings` (owners
  and staff): `AssistantSettingsView` — `remembers_customers` (the
  assistant greets returning customers and knows their upcoming bookings,
  open requests and what earlier conversations were about; true by
  default), `shares_team_notes` (the team's internal notes reach that
  memory; false by default) and `updated_at` (null while the defaults
  apply).
- **Added** `PUT /v1/businesses/{business_id}/assistant-settings` (owners;
  body `{remembers_customers, shares_team_notes}`, both optional with
  those defaults; audited as an update of `assistant_settings`).
- **Changed** (additive) the assistant's tool names gain
  `list_my_bookings` wherever they are listed (an assistant version's
  `tools`, a message's `tool_calls[].tool_name`, the voice tool route
  `POST /v1/voice/tools/list_my_bookings`).

## 2026-10-05 — online-safe migrations: the customer and knowledge lists page in the database

Spec: `8e599fcdb6b69fee`

- **Changed** `GET /v1/businesses/{business_id}/contacts`: customers come
  most recently active first (`last_activity_at` order, kept by every
  message, call, missed call or booking taken for them), a keyset page of
  the database. A search shows the exact matches first (the contact id, the
  full phone number, the exact name without case and accents) and then
  partial matches from a walk of at most 500 customers per request: a page
  may hold fewer rows than asked, even none, while `next_cursor` is set
  ("Load more" searches further back).
- **Changed** `GET /v1/businesses/{business_id}/knowledge`: items come
  the last changed first (`updated_at`), a keyset page of the database;
  `kind` and `is_active` filter in the database.
- **Changed** `ContactDocument` (customer data exports) carries
  `last_seen_at` and `display_name_folded` (version 3).
- **Changed** `GET /v1/admin/clients`: the list reads the client standings
  a worker job refreshes every 15 minutes (summaries, health and each
  client's place in every order) as keyset pages and database counts; a
  client created since the last refresh appears after the next one.
  `generated_at` is when the oldest summary on the page was taken. With
  `search`, `matching_count` counts the matches among the clients one
  request looked at (at most 2,000), and `next_cursor` goes on searching.

## 2026-10-05 — retention: Settings → Privacy periods, the erasure reaches the sub-processors

Spec: `db25fd7f093858f0`

- **Added** `GET /v1/businesses/{business_id}/privacy-settings` and
  `PUT /v1/businesses/{business_id}/privacy-settings` (owners; body
  `{conversation_retention_days, llm_turn_retention_days}`, 30–3650 and
  1–30 days): `PrivacySettingsView` with the two periods (defaults 730 and
  30), `recording_retention_days`, `last_purge` (`ran_at` and the
  `counts` of the latest nightly purge, or null) and `erasure_processors`
  (the sub-processors whose copies are deleted with the platform's own:
  `langfuse`, `elevenlabs`). A shorter period answers 401
  `step_up_required` to a session that signed in long ago. Audited.
- **Changed** `GET /v1/public/chat/{address}` (`HostedChatView`): adds
  `conversation_retention_days` and `llm_turn_retention_days`, the periods
  the hosted chat's privacy notice names.
- The erasure of a contact (`DELETE …/contacts/{contact_id}`, still 204)
  now also queues the deletion of its copies at Langfuse and ElevenLabs
  (audited in the business's log as `langfuse_copies` and
  `elevenlabs_copies`).
- **Changed** `GET /v1/businesses/{business_id}/audit-log`
  (`AuditLogEntryView`): adds `record_count`, how many records a retention
  purge or a deletion at a sub-processor covered (null for other entries).

## 2026-10-05 — legal texts, sub-processor list, terms acceptance

Spec: `64c2050e047d42ec`

- **Added** `GET /v1/legal/subprocessors?language=` (public, cached for
  5 minutes): `SubprocessorListView` with `as_of`, `notice_days` (30), every
  sub-processor in use or announced (`name`, `purpose`, `personal_data`,
  `location`, `added_on`, `removed_on`, `is_in_force`) and
  `upcoming_changes` (`kind` `added` or `removed`, `effective_on`,
  `announced_on`, `notice_from`). English, Russian or Georgian; other
  languages read English. The DPA's section 8 table is rendered from the
  same registry.
- **Added** `GET /v1/legal/{document}?language=&version=` for `terms`,
  `privacy` and `cookies` (public): `LegalDocumentView` with `version` (the
  day it took effect; the version in force when omitted), `language`,
  `available_languages`, `title`, `text` (Markdown), `has_placeholders` and
  `upcoming_version`. 404 for another document or a version without a text.
- **Changed** `GET /v1/auth/login-options`: `terms_version` and
  `privacy_version`, the versions in force (null when there is none).
- **Changed** `POST /v1/auth/otp/verify`: optional `accepted_terms_version`,
  the terms version shown on the code step; a known version not in the future
  is stored on the user and never lowered.
- **Changed** `GET·PATCH /v1/me`: `accepted_terms_version` (null until the
  user signs in with the line shown).

## 2026-10-04 — wave 11 together: guided channels, help and status, teaching, exports, invoices

Spec: `8868b933a62e22f4`

No change of its own: the API description with the five entries below
merged together (the Telegram token check, staff templates per language and
channel health; the help center, support contacts, coach marks and the
platform status page; "Fix this answer", bad rating reasons and the owner's
checks; CSV and full business exports; billing details, numbered invoices
and their PDFs). Each of those entries names the description of its own
change alone.

## 2026-10-04 — guided channels: Telegram token check, staff templates per language, channel health

Spec: `2d10f6638c041f9c`

- **Added** `POST /v1/businesses/{business_id}/channels/telegram/validate-token`
  (owners; body `{bot_token}`): `TelegramBotCheckView` with the bot the
  token opens (`username`, `display_name`, `avatar_data_url`: its profile
  photo inlined as a `data:image/…;base64` URL, the photo's address holds
  the token). Nothing is saved and no webhook is set. 422 with reason
  `telegram_token_format` (not a token's shape) or
  `telegram_token_rejected` (Telegram does not know it), 429 after 20
  checks per business in 10 minutes, 502 when Telegram does not answer.
- **Added** `PUT /v1/businesses/{business_id}/channels/whatsapp/staff-templates`
  (owners; body `{templates: [{name, language_code}]}`, at most 30, one
  per language): replaces the WhatsApp templates staff replies go out in
  after the 24-hour window and answers the WhatsApp `ChannelView`; 422
  with reason `duplicate_template_language` when a language repeats. A
  staff reply takes the template of the conversation's language (exact
  WhatsApp code, then the base language), else the business's main
  language. The single-template `PUT …/whatsapp/staff-template` keeps
  working and now replaces the list with its one template.
- **Changed** `ChannelView` gains `staff_reply_templates`
  (`WhatsAppStaffTemplateView[]`; `staff_reply_template` stays, the main
  language's one), `last_inbound_at` and `last_outbound_at` (the last
  customer message in and the last reply out, to the minute; null before
  the first) and `last_error_reason` (`DeliveryFailureReason`, what the
  channel's last error means; an older error without one reads as
  `credential_rejected`).
- **Changed** `GET /widget.js` takes `data-preview="live"`: the cabinet's
  live preview (the hosted chat page `/c/{address}?preview=1` framed by
  the Channels page of the same origin), shown even while switched off,
  sending and keeping nothing, its colour, corner and language set by
  `window.postMessage` from the framing page.

## 2026-10-04 — help center, support contacts, guidance and the status page

Spec: `6344f91cd124decc`

- **Added** `GET /v1/help/{language}` (public): `HelpCenterView`, the help
  articles of the language served (the one asked for, its base language,
  else English) grouped by `topic` (`getting_started`, `channels`,
  `daily_work`, `account`), each a `HelpArticleCard` (`slug`, `title`,
  `summary`); `available_languages`. Cached 5 minutes.
- **Added** `GET /v1/help/{language}/{slug}` (public): `HelpArticleView`
  with the article's `markdown` and its `related` cards; 404 for an unknown
  slug or language.
- **Added** `GET /v1/help/{language}/search?q=` (public):
  `HelpSearchResults`, the matching articles best first with the passage
  that matched (`snippet`); 422 without `q`.
- **Added** `GET /v1/support/contacts` (public): `SupportContactsView`, the
  platform's support by WhatsApp, Telegram and e-mail with ready links
  (`SUPPORT_*`; null when not set up).
- **Added** `GET /v1/me/help`, `PUT /v1/me/help/coach-marks/{key}`,
  `DELETE /v1/me/help/coach-marks` (204) and `PUT /v1/me/help/changelog`
  (`ChangelogReadBody`): `HelpProgressView`, the coach marks the person
  closed and the newest "What's new" entry read (only moves forward).
- **Added** `GET /v1/platform/status?language=` (public, cached 30 s):
  `PlatformStatusView`, the overall `level` and each component's (`chat`,
  `meta`, `telegram`, `voice`, `cabinet`; `operational`, `maintenance`,
  `degraded`, `outage`) now and over 90 UTC days (`no_data` for days
  without records), the announcements shown now (`is_scheduled` for
  planned maintenance) and those resolved in the last 90 days.
- **Added** `POST /v1/admin/announcements` (201), `PATCH
  /v1/admin/announcements/{announcement_id}` (`resolve: true` ends it) and
  `GET /v1/admin/announcements?limit=&cursor=`: platform admins (step-up;
  audited) tell every owner about an outage, slow service or maintenance
  in en (required), ka and ru.

## 2026-10-04 — teaching from conversations: "Fix this answer", bad rating reasons, the owner's checks

Spec: `1cb3839d3a129574`

- **Added** `GET /v1/businesses/{business_id}/conversations/{conversation_id}/messages/{message_id}/correction`
  (owners; audited as a view of the message): `AnswerCorrectionDraft`, the
  customer's `question` before the assistant answer, the `answer`, its
  `language`, the `suggested_scope` (`faq`, `price`, `hours`, `rule`), the
  `current_fact` the answer came from (`CorrectionFactView`) and the
  `guard_reasons` the reply guard held it back for. A message that is not
  the assistant's is 422 `validation_failed`.
- **Added** `POST …/conversations/{conversation_id}/messages/{message_id}/correction`
  (owners): `AnswerCorrectionRequest` (`scope`; `question` and
  `correct_answer` for `faq`, `hours`, `rule`; `price_minor` of the offer
  `knowledge_item_id`, or of a new offer named `question`, for `price`)
  creates or updates a knowledge item linked to the answer
  (`correction_of`): correcting the same answer again updates the same
  item. `AnswerCorrectionResult` (`item`, `is_new`, `question`,
  `language`). The item joins the pending changes and reaches customers
  with the next "Apply changes".
- **Added** `GET /v1/businesses/{business_id}/answers-to-improve` (owners and
  staff; `limit` 1–20, default 5): `AnswersToImproveView`, conversations
  rated bad whose answer nobody corrected or saved as a check yet, then the
  open unanswered questions (`AnswerToImproveView`, `kind`
  `bad_rating`/`unanswered_question`), with `bad_rating_count` and
  `unanswered_count`.
- **Added** `GET·POST /v1/businesses/{business_id}/autotest-cases` and
  `PATCH·DELETE …/autotest-cases/{case_id}` (owners; POST 201, DELETE 204):
  the owner's own checks, `AutotestCaseView` (`question`, `expectation`
  `must_mention`/`must_not_mention`/`must_hand_off`/`must_create_lead`,
  `expected_text` for the first two, `language`, `source`
  `owner`/`correction`/`unanswered_question`/`bad_rating` with the record it
  was saved from, `is_active`, `last_result` of the newest run). At most 50
  per business (422 `validation_failed`); the same check twice is 409
  `conflict`. Every autotest run, the quick check of "Apply changes"
  included, plays the active checks.
- **Changed** `PUT …/conversations/{conversation_id}/rating` takes `reason`
  (`wrong_info`, `should_hand_off`, `tone`, `too_long`; only with `bad`) and
  `message_id` (the answer it is about; the latest assistant answer by
  default); `ConversationSummaryView` returns `rating_reason` and
  `rated_message_id`.
- **Changed** autotest results: scenario kind `owner_check`, check codes
  `expected_text_missing`, `forbidden_text_mentioned`, `no_lead_created`,
  and `autotest_case_id` on `AutotestScenarioResultView` (the check an
  `owner_check` scenario played).

## 2026-10-04 — exports and data-subject rights: CSV tables, the full export

Spec: `22e97080fdf6241b`

- **Added** `GET /v1/businesses/{business_id}/exports/{table}` (owners,
  after a recent sign-in or step-up: 401 `step_up_required`): the
  cabinet's tables as CSV, `table` one of `bookings`, `leads`, `contacts`,
  `conversations` (one row per message), `audit_log`; the lists' filters
  (`from`, `to`, `status`, `resource_id`, `include_sandbox`, `order`,
  `search`, `view`, `channel`, `action`, `entity`, `actor_id`, `since`,
  `until`) and `language` for the headings. Streamed `text/csv` (UTF-8
  with a byte order mark, values a spreadsheet would run as formulas get
  a leading apostrophe), `Content-Disposition: attachment;
  filename="<table>-<local date>.csv"`; erased customers left out;
  audited once as EXPORT. Unknown `table`: 404.
- **Added** `POST /v1/businesses/{business_id}/business-exports`
  (`StartBusinessExportRequest` `{language?}`, owners, step-up): 202
  `BusinessExportView`; the worker writes a ZIP (a JSON file per
  collection, the CSV tables, README) into the export storage; while one
  is queued or running it is returned. `GET …/business-exports`:
  `BusinessExportList` of the latest ten, a READY one with
  `download_path` (signed, `BUSINESS_EXPORT_LINK_HOURS`).
- **Added** `GET /v1/business-exports/{business_id}/{export_id}/download?token=`
  (no session: the token is the permission): `application/zip`,
  `Cache-Control: no-store`; 404 for a wrong or expired token or a purged
  archive. Audited.
- **Changed** `ContactDataExport` gains `opt_out` (`opted_out_channels`,
  `is_on_suppression_list`) and `records` gains `missed_calls`,
  `outbound_messages`, `inbound_events`, `feedback_requests`;
  `ContactErasureResult` gains `erased_missed_calls`,
  `redacted_outbound_messages`, `redacted_inbound_events`,
  `anonymized_feedback_requests` (additive).

## 2026-10-04 — invoices for the accountant: billing details, numbers, VAT, PDF invoices and receipts

Spec: `4012670dcb9c7de5`

- **Added** `GET /v1/businesses/{business_id}/billing/profile` and
  `PUT /v1/businesses/{business_id}/billing/profile` (owners):
  `BillingProfileView`, the details invoices print for the business
  (`legal_name`, `tax_id`, `address`, `billing_email`, `country_code`),
  `is_saved` (false: the business name and country stand in) and the VAT
  they lead to (`tax_treatment`, `TaxTreatment`: `not_registered`,
  `standard`, `reverse_charge`, `outside_scope`; `tax_rate_basis_points`,
  1800 = 18 %). The `PUT` body takes the five fields (`tax_id`, `address`
  and `billing_email` nullable) and answers 422 for a country that is not
  a country (reason on `country_code`). Saving is audited.
- **Added** `GET /v1/businesses/{business_id}/billing/invoices/{invoice_id}/documents/{document_kind}`
  (owners; `document_kind` `invoice` or `receipt`, optional `language`,
  a BCP 47 tag, else the owner's; written in English, Russian and
  Georgian, other languages read English): the numbered invoice or the
  receipt of a paid one as `application/pdf`, with
  `Content-Disposition: attachment` (`invoice-AW-2026-000042.pdf`) and
  `Cache-Control: private, no-store`. An invoice issued before numbering
  gets its number at the first download; 409 for a receipt of an unpaid
  invoice or a void invoice without a number; 404 for another kind.
  Every download is audited.
- **Changed** `InvoiceView` (`GET /billing`) gains `number` (null until
  issued), `tax` (formatted, null without VAT), `tax_rate_basis_points`,
  `paid_at` and `is_receipt_available`; its `description` is the line in
  the display language without its dates (English, Russian or Georgian,
  worded when the invoice is issued; an older invoice keeps its line as
  issued).

## 2026-10-04 — wave 10 together: value where owners read, the phone loop, reply guard, sessions and support access

Spec: `52268d9934c952f6`

No change of its own: the API description with the four entries below
merged together (summary channels, return on the plan, customer sources
and topics; Undo for booking statuses and resolved handoffs; stored reply
guard verdicts and GUARD_SPIKE; device sessions, the platform admin team
and time-boxed support access). Each of those entries names the
description of its own change alone.

## 2026-10-04 — value where owners read: return on the plan, summary channels, customer sources, topics

Spec: `17fed056871cbc6c`

- **Added** `GET /v1/businesses/{business_id}/value/sources` (owners;
  `period` or `from`/`to` like `/value`): `CustomerSourcesView`, one
  `CustomerSourceRow` per source of the period (`kind`: `tagged`, a tag
  with the channels it came through; `untagged`, one channel's
  conversations without a tag; `other`, the smallest tags folded together
  with `source_count`) with `conversation_count`, `booking_count` (kept
  bookings made in the period in the source's conversations),
  `request_count` and `estimated_value_minor` (own values, the rest at the
  average check; null when nothing prices them).
- **Added** `GET /v1/businesses/{business_id}/value/topics` (owners and
  staff): `ConversationTopicsView`, what customers asked about in the last
  30 days as the nightly grouping stored it: `TopicLanguageView` per
  customer language with up to 12 `ConversationTopicView` (`label` in the
  owner's language, `conversation_count`, `unanswered_count`). Never
  grouped: no window, no groups.
- **Changed** `ValueModel` (`GET /value`) and `ValueReportView` gain
  `plan_cost_minor` (the plan's price for the period's days) and
  `return_multiple` (the estimate divided by it, one decimal); both null
  when the plan is priced in another currency or free, and for staff.
- **Changed** `DigestPreferencesView` gains `channels` (`DigestChannel`:
  `email`, `push`, `telegram`, `whatsapp`), `telegram_chat`,
  `telegram_chats` (`DigestTelegramChatView`, the business's chats linked
  to the platform bot), `is_telegram_ready`, `whatsapp_number`,
  `suggested_whatsapp_number` and `is_whatsapp_ready`; the
  `PUT /digest-preferences` body takes optional `channels`,
  `telegram_chat` and `whatsapp_number` (null keeps what is stored) and
  answers 422 with reason `telegram_not_available`,
  `telegram_chat_not_linked`, `whatsapp_not_available` or
  `whatsapp_number_missing` when a chosen channel cannot reach the owner.
- **Changed** `InboxItemView` and `ConversationDocument` gain
  `acquisition_source`, where the customer came from (a link's tag, a QR
  code, an ad, `tel-<digits>` for the line called).
- **Changed** the widget's `POST /v1/widget/{business_id}/messages` and
  `POST /v1/widget/{business_id}/handoff` bodies take an optional
  `source` (at most 200 characters; normalized to a tag, an unreadable one
  is ignored).

## 2026-10-04 — Undo for booking statuses and resolved handoffs

Spec: `3429cf21c95a5ea5`

- **Added** `POST /v1/businesses/{business_id}/bookings/{booking_id}/revert-status`
  with `RevertBookingStatusRequest` (`status`: the status being undone):
  the booking gets back the status it had before the last change staff
  made in the cabinet (confirmed, completed, no-show, cancelled), within
  10 minutes of it and once. A booking that freed its time takes it again
  only if it is still free; otherwise 409 with the reason `slot_taken`
  (details: the place's id). Other 409 reasons: `nothing_to_undo` (no
  staff change to undo, or the customer changed it), `status_changed`
  (details: the current status), `undo_expired` (details: the window in
  minutes), `place_gone`. Returns the `BookingView`.
- **Added** `POST /v1/businesses/{business_id}/handoffs/{handoff_id}/reopen`:
  a resolved handoff waits for a person again with the status it had
  before (`notified` when that is unknown), and its conversation goes back
  to `handoff`. Reopening an open handoff is harmless. Returns the
  `HandoffListItem`.
- **Changed** the live event stream gains `handoff.reopened` (the handoff
  and its conversation); `POST …/bookings/{id}/cancel` from the cabinet
  and `POST …/handoffs/{id}/resolve` now remember who did it, so it can
  be undone (resolving is audited).
- **Changed** `BookingDocument` (schema version 3) gains
  `last_status_change` and `HandoffDocument` (schema version 3)
  `status_before_resolve` and `resolved_by` (all optional).

## 2026-10-04 — reply guard beyond numbers: stored verdicts, GUARD_SPIKE

Spec: `a4d3fb74c835b55f`

- **Changed** `MessageView` (`GET /v1/businesses/{business_id}/conversations/{conversation_id}`
  and `.../{conversation_id}/messages`) gains `guard` (`MessageGuardView`, null when
  there is nothing to show): on an assistant reply its `verdict` (`clean`,
  `rewritten`, `handed_off`), `reasons` (`unverified_values`,
  `unsupported_claims`, `personal_data`), the `unverified_values` and the
  checked `claim_findings` (`ClaimFindingView`: `claim`, `topic` —
  `policy` or `availability` — and `verdict` — `supported`,
  `unsupported` or `unchecked`); on a customer message its
  `injection_flag` (`instruction_override`, `role_change`,
  `prompt_extraction`, `data_exfiltration`, `fake_platform_text`).
- **Changed** `AdminClientSummary` (`GET /v1/admin/clients`,
  `GET /v1/admin/clients/{business_id}`) gains `guard_activity`
  (`ClientGuardActivity`: `checked_replies`, `rewritten_replies`,
  `handed_off_replies`, `injection_flags` of the last 7 days).
- **Changed** `ClientHealthIssue` gains `guard_spike`: at least five
  replies held back and at least one in six, or at least ten messages
  flagged as prompt injection, in the last 7 days.
- **Changed** `MessageDocument` (schema version 4) and
  `AssistantVersionDocument` (schema version 5, `facts[].is_imported`)
  gain optional fields; older rows read as they are.

## 2026-10-04 — device sessions, the platform admin team, support access

Spec: `f29245886ba350fb`

- **Added** `GET /v1/me/sessions` (`UserSessionList`): the person's
  signed-in devices (`UserSessionView`: `device` with `kind`, `browser`,
  `operating_system` read from the User-Agent; `created_at`/`created_ip`,
  `last_seen_at`/`last_seen_ip`, `auth_level`, `expires_at`,
  `idle_expires_at`, `is_current`), the most recently used first.
  `DELETE /v1/me/sessions/{session_id}` (`204`; another person's or an
  unknown id: `404`) and `POST /v1/me/sessions/revoke-others`
  (`RevokedSessionsView.revoked_count`) end sessions; each is audited
  `session_revoked`.
- **Changed** sessions end when unused: 7 days for owners and staff
  (`SESSION_IDLE_TIMEOUT_SECONDS`), 12 hours for platform admins, whose
  sessions also end after 24 hours whatever happens
  (`ADMIN_SESSION_*`). The next request of an ended session gets `401`.
  Sign-ins from a new device send the person a personal notice (staff
  alert with the deep link target `account_security`).
- **Added** the platform admin team: `GET·POST /v1/admin/team`
  (`PlatformAdminTeamView`: each `PlatformAdminView` with `added_by`, null
  for one bootstrapped from the lists; add by `phone_number` or `email`
  with a `role`: `super`, `support_readonly`, `billing`; step-up; the same person
  twice: `409`), `PATCH /v1/admin/team/{admin_id}` (`role`) and
  `DELETE /v1/admin/team/{admin_id}` (`204`); leaving the team without a
  `super` admin: `409`. Every change is audited `platform_admin_changed`.
  Only `super` manages the team.
- **Changed** `CurrentUserView` (`GET /v1/me`) gains
  `platform_admin_role` and `platform_admin_permissions`; the admin pages
  check the role's permission (`403` without it): `billing` sees clients
  and metrics, `support_readonly` sees clients and operations and opens
  cabinets read-only, `super` does everything.
- **Changed** `PLATFORM_ADMIN_EMAILS` and `PLATFORM_ADMIN_PHONE_NUMBERS`
  only bootstrap the team: the first listed person to sign in while the
  team has no `super` admin becomes one; other listed people get admin
  pages only once added on the Team page.
- **Breaking** `POST /v1/admin/clients/{business_id}/open` needs a body
  `OpenClientCabinetRequest` with a `reason` (8–300 characters; without
  it: `422`) and opens a 60-minute read-only look into the cabinet
  (`ClientCabinetAccess` gains `support_access_grant_id`, `expires_at`,
  `can_write`). Platform admins' requests to `/v1/businesses/{id}/…`
  without an open look get `403` with the reason `support_access_required`;
  changes during a look get `403` `support_read_only` unless the owner
  allowed changes (and the admin is `super`). Exports of contact data
  count as changes. Migration path: the cabinet asks for the reason in
  the "Open cabinet" dialog; scripts send `{"reason": "…"}`.
- **Added** `DELETE /v1/admin/clients/{business_id}/access` (`204`): the
  admin leaves the cabinet before the hour is over.
- **Added** the owner's side: `GET /v1/businesses/{id}/support-access`
  (`SupportAccessView`: open looks with who, why and until when, the
  consent to changes, and whether the viewer is support),
  `PUT …/support-access/write-access` (`is_allowed`, `hours` 1–168,
  a day by default; owners only, step-up to allow) and
  `DELETE …/support-access` (`204`; ends every look and the consent).
  Starts and ends are audited `support_access_start` and
  `support_access_end` with the address; the team gets a staff alert
  when a look starts.

## 2026-10-04 — wave 9 together: reply speed, any language, outbox everywhere, platform operations

Spec: `26522d8605b0100d`

No change of its own: the API description with the four entries below
merged together (reply speed and SLOW_REPLIES, answers in any language
with the language autotests, every customer message through the outbox
with its delivery on staff replies, platform health and incidents for the
admin). Each of those entries names the description of its own change
alone.

## 2026-10-04 — reply speed: measured waits, admin p50/p95, SLOW_REPLIES

Spec: `1554f2578d368a1e`

- **Changed** `AdminClientSummary` (`GET /v1/admin/clients`,
  `GET /v1/admin/clients/{business_id}`) gains `reply_speed`
  (`ClientReplySpeed`: `reply_count`, `p50_ms`, `p95_ms` and `channels`,
  one `ChannelReplySpeed` per channel, the busiest first): how long the
  client's customers waited for the assistant in the last 7 days, from
  their first unanswered message to the stored reply. Percentiles are
  null without measured replies.
- **Changed** `ClientHealthIssue` gains `slow_replies`: at least 10
  measured replies in the last 7 days and a 95th percentile above 15 s.
- **Changed** `MessageDocument` (schema version 3) gains `channel`,
  `reply_latency_ms` (null when not measured: test chats, calls, older
  messages), `llm_round_count` and `is_fallback_model` (another provider's
  model answered while the version's own was failing). The transcript
  also shows a short "one moment" assistant message when a reply took
  longer than `CHAT_TURN_DEADLINE_SECONDS`.

## 2026-10-04 — answers in any language, language autotests

Spec: `fe2d68a30e5c6ddf`

- **Changed** (additive) `AutotestScenarioKind` gains `foreign_language`
  (the customer writes a language the business did not list) and
  `transliterated` (a business language typed in Latin letters); niches
  list them in `autotest_kinds`, and `POST …/autotests` accepts them in
  `kinds`. `transliterated` applies only when a version language is
  Georgian, Russian, Ukrainian, Armenian or Hebrew.
- **Changed** (additive) `AutotestCheckCode` gains
  `wrong_disclosure_language`: the AI disclosure of the first reply was
  not in the customer's language.
- **Changed** the `language` of conversations, messages and test-chat
  replies is the language the customer writes in, any BCP 47 tag, also
  one the business did not list (it was always one of the business
  languages before).

## 2026-10-04 — every message to a customer through the outbox

Spec: `3d1409bdbac41e3a`

- **Added** `MessageView.delivery` (`MessageDeliveryView`: `state`
  `sending` | `retrying` | `delivered` | `failed`, `failure_reason`
  (`DeliveryFailureReason`: `rate_limited`, `provider_unavailable`,
  `recipient_refused`, `template_rejected`, `channel_disconnected`,
  `credential_rejected`, `not_configured`, `expired`), `attempts`,
  `next_attempt_at`, `delivered_at`) on staff replies sent through a
  messenger: the conversation card and its message pages show how the
  reply travels. Website chat replies and every other message carry
  `null`.
- **Changed** (additive) `POST /v1/businesses/{business_id}/conversations/{conversation_id}/messages`:
  `delivery` `sent` / `sent_as_template` now means queued in the outbox
  (the worker sends it with retries; the message's `delivery` follows
  it). A provider outage no longer answers `502`: the reply is stored and
  retried. A WhatsApp template Meta refuses is no longer refused in the
  request (`409` with the code `template_rejected`); the reply is stored
  and its `delivery` ends `failed` with `template_rejected`.

## 2026-10-04 — platform health and incidents for the admin

Spec: `3ed157339d00b407`

- **Added** `GET /v1/admin/system` (platform admins): `AdminSystemView`
  with the platform alerts firing or resolved within a day
  (`AlertStateView`: code, severity, figure against threshold, runbook),
  the worker pulses (`WorkerPulseView`, `is_stale`), each queue lane's
  due, scheduled, running and dead jobs with the oldest wait
  (`LaneView`), the dead letters per job name (`DeadJobTally`; the jobs
  themselves stay on `GET /v1/admin/jobs?status=dead`), channels in
  ERROR and Meta tokens running out within 14 days (`ChannelIssueView`),
  the database size per table (`TableSizeView`, null `database_bytes`
  without a database), and the last backup and restore drill
  (`MaintenanceRunView`, `is_backup_overdue`).
- **Added** `POST /v1/admin/incidents` (platform admins, step-up): records
  an outage, a degradation or a personal data breach for the businesses
  named (`affected_business_ids`), writes an audit entry (`incident`) in
  each business's log and, for a breach, sends the DPA 12.1 notice to the
  owners of those businesses (`approximate_subject_count`,
  `approximate_record_count`, `notice_texts` with English required).
  Answers `201` with `IncidentView` (`notified_owner_count`,
  `notice_languages`); `422` when a business does not exist, a time is in
  the future or the breach notice is incomplete.
- **Added** `GET /v1/admin/incidents?limit=&cursor=`: the incident log,
  newest first (`IncidentPage`).

## 2026-10-04 — wave 8 together: setup guide, customer media, two-factor sign-in, services

Spec: `94b41f2ced788361`

No change of its own: the API description with the four entries below
merged together (two-factor sign-in with step-up, bookable services with
booked value, the setup guide and setup options, customer voice messages,
photos and places). Each of those entries names the description of its
own change alone.

## 2026-10-04 — two-factor sign-in, step-up, admin rights read per request

Spec: `9e7869ca5b5edff3`

- **Breaking** (`api-breaking`) `POST /v1/auth/otp/verify` answers either
  the session (`LoginSessionView`, unchanged for people without an
  authenticator) or, for people with an authenticator and for every
  platform admin, `MfaRequiredView` (`mfa_required: true`,
  `mfa_challenge`: id, five-minute lifetime, `requires_enrollment`) and
  no token. Migration path: when `mfa_required` is true, send the
  authenticator code (`code`) or a recovery code (`recovery_code`) to
  **Added** `POST /v1/auth/mfa/verify`, which answers the session; an
  admin without an authenticator first gets its secret and setup link
  from **Added** `POST /v1/auth/mfa/enroll`, and the session answer then
  carries the ten new `recovery_codes` (shown once).
- **Changed** `LoginSessionView` gains `auth_level` (`one_factor` |
  `two_factor`) and `recovery_codes`; `CurrentUserView` (`GET /v1/me`)
  gains `auth_level`.
- **Added** Account → Security: `GET /v1/me/security`,
  `POST /v1/me/mfa/totp` (start setting up an authenticator),
  `POST /v1/me/mfa/totp/confirm` (first code; answers the recovery
  codes), `DELETE /v1/me/mfa/totp` (`204`) and
  `POST /v1/me/mfa/recovery-codes` (a new set). Every change is in the
  audit log as `mfa_changed` (new `AuditAction` value, on entries that
  name no business: the business audit log never lists them).
- **Added** step-up: exporting or erasing a contact's data, team changes,
  connecting a channel (not the website chat, which holds no outside
  account's credentials), `PUT …/security`, setting up an authenticator,
  the admin opening a client's cabinet and starting a key rotation answer
  `401 authentication_required` with the reason `step_up_required`
  (detail: the window in seconds) and
  `WWW-Authenticate: Bearer error="insufficient_user_authentication"`
  when the session last proved its person more than
  `STEP_UP_MAX_AGE_SECONDS` (600) ago. The session stays valid: confirm
  with `POST /v1/auth/step-up` (`totp`, or a login code sent to the
  person's own phone or e-mail) and `POST /v1/auth/step-up/verify`, then
  repeat the request. A wrong code is `422 validation_failed` with the
  reason `wrong_code`.
- **Added** `GET` and `PUT /v1/businesses/{business_id}/security`
  (`require_mfa_for_members`; changing it is owner-only and turning it on
  needs the owner's own two-factor session). While it is on, members
  signed in with one factor get `403 access_denied` with the reason
  `mfa_required` on the business's routes.
- **Changed** admin routes (`/v1/admin/…`) refuse a session without two
  factors with `403 access_denied`, reason `mfa_required`, and read admin
  rights from `PLATFORM_ADMIN_EMAILS` / `PLATFORM_ADMIN_PHONE_NUMBERS` at
  every request (someone taken off the lists is refused at once).

## 2026-10-04 — bookable services, performers, seasonal rates and booking value

Spec: `8999d057f062d358`

- **Added** knowledge items of kind `service`, `package` and `room_type`
  say what a booking of them takes: `buffer_minutes` (0 to 240, services
  and packages: the performer's break after the visit),
  `performer_resource_ids` (resources of the business that perform it)
  and, for room types, `seasonal_rates` (`starts_on`/`ends_on` as
  `"MM-DD"`, every year, over New Year when the end comes first;
  `nightly_rate_minor`; optional `name`; at most 24, never overlapping).
  In `POST /v1/businesses/{business_id}/knowledge`,
  `PATCH …/knowledge/{item_id}`, `PUT …/profile/steps/{step}` and in
  `KnowledgeItemDetails` / `KnowledgeItemView`. A new performer list is
  the whole truth: a resource left out stops naming the item too.
- **Added** resources name the services and packages they perform
  (`serves_item_ids`) and a room its room type (`room_type_item_id`), in
  `POST …/resources`, `PATCH …/resources/{resource_id}` (null clears the
  room type) and `ResourceView`. Both editors show every link, from
  either side.
- **Added** `GET …/availability?service_item_id=`: the service sets the
  visit length and buffer and limits the slots to its performers;
  `AvailabilityResult.service` names it (with its performers),
  `AvailabilityResult.services` lists the bookable offers when none is
  named, and a stay of a priced room type carries `stay_quote` (every
  night at its season's rate). `POST …/bookings` (manual booking) takes
  `service_item_id` too.
- **Added** `BookingView.service_item_id`, `service_title`, `value_minor`
  and `currency_code`: what was booked and what it is worth (a service's
  price, a stay's nights at their seasonal rates).
- **Added** `DashboardStats.booked_value` and `after_hours_booked_value`
  (per currency: value and number of valued bookings made in the period,
  cancelled and no-shows left out; owners only, staff get empty lists), and `ValueTotals.valued_booking_count`,
  `booked_value_minor` and `revenue_source` (`booked_values`, `mixed`,
  `average_check`) in the value model: bookings with a value count at
  their value, the others at the average check.
- **Added** booking refusal reason codes `unknown_service`,
  `ambiguous_service`, `unknown_resource`, `ambiguous_resource` and
  `not_performed`; their `details` are ids (the matched offers or
  resources), never names.
- **Breaking** (`api-breaking`) `duration_minutes` of a knowledge item is
  5 to 720 minutes (one booking of a service) instead of 1 to 43200 in
  the create and update requests. Migration path: a length outside that
  range (a room type's "1440") goes into an attribute instead
  (`attributes: [{"key": "duration_minutes", "value": "1440"}]`), as the
  stored items were moved on read (knowledge items schema version 2).
  The cabinet sends no such lengths.

## 2026-10-03 — the setup guide, self-serve setup and setup reminders

Spec: `4f97fcafe0dae3be`

- **Added** `SetupView.guide` (`SetupGuideView`) on
  `GET /v1/businesses/{business_id}/setup`: the steps after the launch
  (`steps_after_launch`: `phone_test`, `second_channel`, `share`), the
  guide's `next_step` and `next_action`, `percent`, `minutes_left`,
  `is_complete`, `is_dismissed`, and the phone check
  (`is_phone_check_listening`, `phone_check_until`, `phone_tested_at`).
  `SetupStepCode` gains `phone_test`, `second_channel` and `share`;
  `SetupActionTarget` gains `phone_test` and `share`; both are read by
  the cabinet of this release, and a client that does not know a step
  can show its `title`, `description` and `action.label`.
- **Added** `POST /v1/businesses/{business_id}/setup/phone-check`
  (listen half an hour for the owner's own message from a phone),
  `POST …/setup/share-marks/{mark}` (`printed_qr`, `downloaded_qr`;
  `204`), `PUT`/`DELETE …/setup/guide-dismissal` (owners; `409` while the
  guide is unfinished; `DELETE` answers `204`) and
  `GET`/`PUT …/setup/reminders` (`SetupRemindersView`; `PUT` owners,
  body `{"is_on": false}` turns the activation reminders off).
- **Added** `ActivationEventKind.first_after_hours_booking`, celebrated
  once through `POST …/setup/milestones/{kind}/celebrate` like the other
  milestones.
- **Added** `StaffLinkTarget` values `overview`, `setup`, `channels`,
  `share` and `billing` (signed links of milestone notices and setup
  reminders, resolved by `GET /v1/businesses/{business_id}/notification-links/{token}`).
- **Added** setup options: `PlanQuote.setup_options`
  (`SetupOptionQuote`: `self_serve` free, `done_for_you` the plan's
  setup fee), `SubscriptionView.setup_option` and
  `onboarding_requested_at`, `AdminClientSummary.setup_option` and
  `onboarding_request` (`OnboardingRequestView`), and
  `setup_option` in the body of
  `POST /v1/businesses/{business_id}/billing/subscribe` (default
  `self_serve`).
- **Changed** the one-time setup fee is invoiced only for a
  `done_for_you` subscription (an onboarding request reaches the
  platform team); `self_serve` and subscriptions from before the choice
  (`setup_option: null`) pay none. `PlanQuote.setup_fee` stays the
  `done_for_you` fee.

## 2026-10-03 — voice messages, photos and places of customers

Spec: `76e1e3904dd01540`

- **Added** `GET /v1/businesses/{business_id}/media/{media_id}`: a voice
  message or photo a customer sent, for owners and staff of the business
  (`404` for another business's file, or one the retention purge or an
  erasure removed). The type is read from the file itself; the answer is
  `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`,
  `Content-Disposition: inline` and a sandboxing CSP. Each opening is in
  the audit log (`view`, entity `message_media`).
- **Changed** (additive) `MessageView.attachments`: the voice messages
  (`media_id`, `duration_seconds`, `transcript`), photos (`media_id`,
  `media_type`), places (`location`, `map_url`) and other files of a
  customer message, with `problem` when the assistant could not read one
  (`unsupported_kind`, `too_large`, `too_long`, `unavailable`,
  `unrecognized_format`, `not_understood`) and `is_media_deleted` after
  the retention purge.
- **Changed** (additive) `ConversationSummaryView` and `InboxItemView`:
  `last_message_attachment`, the kind of what the last message carried
  besides text (`audio`, `image`, `location`, `contact`, `sticker`,
  `other`); `last_message_text` includes a voice message's transcript.
- **Changed** (additive) `UsageKind`: `transcription_seconds` (voice
  messages transcribed) in admin usage views.

## 2026-10-03 — widget messages are answered by the worker

Spec: `66ff36e8e31c29a8`

- **Breaking** `POST /v1/widget/{business_id}/messages` answers `202`
  with `WidgetMessageAcceptedView` (`event_id`: the message in the
  inbox) instead of `200` with the answer (`WidgetReplyView`, removed).
  The message is stored and queued in one transaction and a worker
  answers it like every channel's message, so a slow model never holds a
  request thread. Migration path: poll `GET .../messages?after=<cursor>`
  (as the widget already did for staff messages) until the assistant's
  answer, or a staff message, arrives; `/widget.js` of this release shows
  the typing dots meanwhile. A widget script cached from before takes the
  `202` as an answer without text and shows the answer at its next poll.
  Errors are unchanged (`404` unknown business or widget off, `409` the
  assistant is not live, `422`, `429`), and `409` now comes before the
  message is stored.
- **Changed** the owners' test chat
  (`POST /v1/businesses/{business_id}/test-chat`) answers `429` with
  `Retry-After: 5` when `TEST_CHAT_MAX_CONCURRENCY` test chats are
  being answered by the API instance and none frees up within 10 s
  (before, every test chat simply took a request thread for its whole
  answer).
- **Changed** `GET /readyz` (not in the description): a pool without a
  free connection reports the pool and database checks as `degraded`
  (with `exhausted_seconds`) and stays `200` for 30 s; only an unreachable
  database, a missing migration or a pool exhausted for longer is `503`.

## 2026-10-03 — one source of truth: counts, autotest verdicts, exchange rates, channel addresses

Spec: `35be369c1300ba27`

- **Removed** (`api-breaking`) `GET /v1/businesses/{business_id}/inbox-counts`.
  No client read it since the badges moved to `…/attention-counts`; it
  counted handoffs and leads, while the inbox tabs count conversations.
  Migration: read `needs_person` and `requests` of
  `GET /v1/businesses/{business_id}/attention-counts` (or
  `…/inbox/counts`).
- **Changed** `GET /v1/businesses/{business_id}/attention-counts` and
  `GET /v1/businesses/{business_id}/inbox/counts` answer the same
  `InboxAttentionCounts`, counted once (`CountInboxAttentionUseCase`):
  conversations waiting for the team by inbox view — `needs_person`,
  `requests`, `unassigned`, `mine` (the viewer's) — plus
  `unconfirmed_bookings` and `channel_errors`. The inbox badge is
  `needs_person + requests`, the sum of its two tabs. `…/inbox/counts`
  gains `business_id`, `unconfirmed_bookings` and `channel_errors`.
- **Deprecated** (sunset 2027-04-01, removed in `/v2`) the old names of
  `…/attention-counts`: `open_handoff_count`, `new_lead_count`,
  `unconfirmed_booking_count`, `channel_error_count`. They stay in the
  answer with the numbers of `needs_person`, `requests`,
  `unconfirmed_bookings` and `channel_errors` (open handoffs and new
  leads are now counted by their conversation, as the tabs count them).
- **Added** `autotest_verdict` (`ClientAutotestVerdict`: version number,
  `is_passed`, `passed_count`, `scenario_count`, `average_score`) to
  `AdminClientSummary`: the verdict the active version (published, else
  the latest tested) stores, the same one its version page shows.
  `AUTOTESTS_FAILED` now follows it: a run that passed with a scenario
  failed is no longer an issue. `failed_tests` is that run's failed
  scenarios.
- **Added** `check_codes` (`AutotestCheckCode`) and `low_criteria`
  (`JudgeCriterion`) to `FailedAutotestView`, and `check_codes` to
  `AutotestScenarioResultView`: why a scenario failed, as codes the
  cabinet renders in every language (`judge_notes` and `check_notes`
  stay English text).
- **Added** `link_state` (`ChannelLinkState`: `linked`,
  `missing_public_address`; null for a channel that is not connected or
  has no link of its own) to `ChannelView`: whether customers can be sent
  a link to the channel, by the same rule the share links follow. A
  connected WhatsApp or Instagram whose public address the platform never
  learned is `missing_public_address`; the share links keep skipping it
  with the `reconnect_channel` gap.
- **Added** `rate_value` (the exact rate as a decimal string, e.g.
  `"2.9552"`), `sources` (`ExchangeRateSource` codes: `nbg`, `ecb`,
  `planning`), `is_derived` and `is_stale` to `ExchangeRateQuote` (plan
  quotes, a client's cost report). Rates are now dated rows refreshed
  daily from the National Bank of Georgia and the European Central Bank;
  a pair no bank publishes is the inverse of its opposite or a cross rate
  through the euro (`is_derived`), and a rate older than four days is
  `is_stale` (its `rate_date` says how old). `rate` stays, as the same
  number in JSON (compute with `rate_value`). Prices outside the euro and
  the lari (e.g. USD for the United States) are now estimated with such a
  rate (`is_estimated`), and a client's dollar provider costs convert into
  every subscription currency, so the admin margin is known.
- **Changed** `negative_margin` (`ClientHealthIssue`) is raised only for a
  client that pays (not during a free trial or without a subscription):
  a trial costs the platform by design, and with every margin now known it
  would otherwise make every trialing client critical.

## 2026-10-03 — changes not live yet and one "Apply changes"

Spec: `4d1d0054fa6321f1`

- **Added** `GET /v1/businesses/{business_id}/assistant/pending-changes`
  (owners and staff; `?language=`; `PendingChangesView`): what customers do
  not get yet, change by change against the live version (`is_live`,
  `live_version_number`, `has_unapplied_changes`, `count` and `changes`).
  Each `PendingChange` has an `area` (`profile`, `hours`, `special_days`,
  `answers`, `offer`, `questions`, `resources`, `booking_rules`, `links`,
  `languages`, `calls`, `conversation`) and an `action` (`added`,
  `changed`, `removed`), and names what it is about: `field`, `weekday`,
  `link_kind`, `date`, `item_kind` or the owner's own words in `subject`.
  A changed offer item has `detail` (`price` with `before` and `after`,
  or `details`). Before the first go-live `is_live` is false and the list
  is empty.
- **Changed** `has_unapplied_changes` of `GET …/assistant/apply` (and of
  the setup's `apply`) now means exactly "the pending changes are not
  empty": a removed knowledge item counts, and an edit undone before
  applying does not.
- **Changed** `POST …/assistant/apply` after the first go-live checks the
  changed scenarios and three core ones instead of every scenario
  (`checks_total` is smaller); the first go-live still plays them all.
- **Changed** `GET …/assistant-versions` leaves out drafts discarded when a
  newer version went live; `GET …/assistant-versions/{version_id}` still
  reads them.
- **Added** the live event `assistant.apply` (ids of the apply and its
  version) whenever "Apply changes" moves to another stage.

## 2026-10-03 — growth analytics: the founder's metrics and cabinet telemetry

Spec: `9863d1587ceea5c9`

- **Added** `GET /v1/admin/metrics` (platform admins; `AdminMetricsView`;
  `from` and `to` as UTC days, default the last 90 days, at most 731;
  `country`, `niche`, `source`): the funnel of the period's sign-ups
  (owners, not invited staff or admins) with shares of the sign-ups and of
  the step before, median time to go live, activation within 7 days,
  trial to paid, the setup tunnel per screen, monthly cohorts with the
  paying share per month since sign-up, acquisition sources, MRR at the
  start and end of the period with new, reactivation, expansion,
  contraction and churn movements in euros (official rates; currencies
  without one are named), ARPA, gross margin from the client cost
  reports, the cabinet's Web Vitals (p75 per route template and device
  class with Google's rating) and the filter choices. 422 for a day the
  calendar does not have or a period over two years.
- **Added** `POST /v1/telemetry/events` (signed in; 202
  `TelemetryBatchReceipt`): up to 50 reports, each a Web Vital (`lcp`,
  `inp` in ms, `cls` in ten-thousandths; route template; device class) or
  a tunnel step (entered or completed; a business only of the person's
  own team is kept). 429 past 30 batches a minute per person; samples are
  purged after 90 days.
- **Changed** `POST /v1/auth/otp/verify` takes an optional
  `signup_attribution` (utm_*, `referral_code`, `source_tag`,
  `referrer_host`, `landing_path`, `first_seen_at`), kept on the account
  only when the sign-in creates it; unknown fields are a 422.

## 2026-10-03 — encryption key rotation for platform admins

Spec: `0ee9211ca86eb0d0`

- **Added** `GET /v1/admin/security/encryption-keys` (platform admins;
  `EncryptionKeysView`): how many keys `ENCRYPTION_KEYS` holds (never the
  keys) and the latest re-encryption run (`KeyRotationView`, `null`
  before the first one) with its counts: secrets checked, already under
  the current key, re-sealed, unreadable, Telegram webhooks renewed and
  failed.
- **Added** `POST /v1/admin/security/encryption-keys/rotate` (platform
  admins; 202 `KeyRotationStarted`): queues the `rotate_encrypted_secrets`
  job that seals every stored channel and calendar secret again with the
  newest key; audited; 409 while a run is queued or running.

## 2026-10-03 — value of the assistant: value model, average check, digests, reports

Spec: `26b326955b930a9a`

- **Added** `GET /v1/businesses/{business_id}/value` (owners and staff;
  `period` = `today`, `7d`, `30d`, `90d`, `this_month`, `last_week` or
  `last_month`, or local dates `from` and `to`; default the last 30 days;
  `ValueModel`): what the assistant did in the period and in the period
  before it (`current`, `previous`: conversations and those after hours,
  customer messages, assistant replies, calls, bookings and the
  assistant's bookings that are still on, requests, conversations that
  needed a person, staff minutes saved, `estimated_revenue_minor`), with
  `value_basis` (`bookings` or `requests`), the average check used and
  its `average_check_source` (`owner`, `niche_default`, `none`), the
  niche's `typical_check_minor` and the staff time rates. Staff get every
  amount as null and the source `none`.
- **Added** `GET` and `PUT /v1/businesses/{business_id}/value/settings`
  (owners; `ValueSettingsView`, body `ValueSettingsRequest`): the average
  check per booking (or order) in minor units of the business currency;
  null clears it. Audited.
- **Added** `GET` and `PUT /v1/businesses/{business_id}/digest-preferences`
  (owners, their own; `DigestPreferencesView`, body
  `DigestPreferencesRequest`): daily digest (off by default), weekly digest
  and monthly report (on by default), with the e-mail and the number of
  devices they reach. Audited.
- **Added** `GET /v1/businesses/{business_id}/value-reports` (owners;
  `kind` = `monthly` (default), `weekly` or `daily`; `limit`, `cursor`;
  `ValueReportPage`, newest period first) and
  `GET /v1/businesses/{business_id}/value-reports/{report_id}`
  (`ValueReportView`): the stored digests and monthly reports with their
  `delivery` (`sent`, `no_recipients`, `quiet`).
- **Added** `GET /v1/businesses/{business_id}/today-queue` (owners and
  staff; `TodayQueue`): today's bookings that are on, still to start and
  waiting for confirmation.
- **Changed** `StaffLinkTarget` gains `report` and `StaffLinkView` gains
  `value_report_id`: a digest's link opens its report.

## 2026-10-03 — feedback after visits, the Google review link, STOP for unrequested messages

Spec: `6d36133d537ca729`

- **Added** `GET` and `PUT /v1/businesses/{business_id}/review-settings`
  (owners; `ReviewSettingsView`, body `ReviewSettingsRequest`): feedback
  after visits on or off (off by default), `delay_minutes` after the
  visit ends (15 to 4320, default 120), the approved WhatsApp utility
  template for a closed 24-hour window (`^[a-z0-9_]+$`), and
  `google_review_url` (http or https; kept as the profile's link of kind
  `google_review`; 422 while the business has no profile). The view adds
  `is_whatsapp_connected`, `is_link_tracked` (the platform's public
  address is set, so link visits are counted) and `template_previews` (the
  body to register with Meta, its parameter `{{1}}` the business name, and
  what customers read, per language). The change is audited.
- **Added** `GET /v1/businesses/{business_id}/review-stats` (owners;
  `ReviewStatsView`, the last 30 days): `asked_count`, `answered_count`,
  `average_score` (null without answers), `score_counts` (1 to 5),
  `review_opened_count`, `skipped_count`, `failed_count`.
- **Added** `GET /v1/businesses/{business_id}/feedback-requests` (owners;
  `limit`, `cursor`; `FeedbackRequestPage` of `FeedbackRequestView`,
  newest first): the visit, the customer's name, `status` (`sent`,
  `answered`, `skipped`, `failed`), `skip_reason`, `channel`, `score`,
  `review_clicks`, `conversation_id`. Audited as a view of personal data.
- **Added** `GET /v1/public/reviews/{token}` (no authentication): 302 to the
  business's Google review page, counting the customer's visit (a
  messenger's link preview is not counted); 404 for an unknown token or a
  removed review link; `Cache-Control: no-store`, `X-Robots-Tag: noindex`,
  `Referrer-Policy: no-referrer`.
- **Changed** `ContactSummaryView` gains `opted_out_channels` (where the
  customer sent STOP). `BusinessLinkKind` gains `google_review`: the
  profile's links include the review page set in Settings → Reviews.

## 2026-10-03 — the conversation card names its assignment

Spec: `0a10bb03c28bdc5a`

- **Changed** `ConversationDetailView`
  (`GET /v1/businesses/{business_id}/conversations/{conversation_id}`)
  gains `assignment` (`ConversationAssignmentView`: the assignee, who
  assigned and when, whether it was automatic, and the
  `assignment_revision` that `POST …/assign` must name), so the cabinet's
  conversation view assigns without reading the inbox list first.

## 2026-10-03 — handoffs the platform creates are read in each reader's language

Spec: `eced8ca70fcbb8b2`

- **Added** `summary_code`, `quoted_text` and `flagged_values` on
  `HandoffListItem` (`GET /v1/businesses/{business_id}/handoffs` and the
  resolve answer). A handoff the platform created itself (the model
  declined or was unavailable, an answer held back for figures missing
  from the business data, a call that named such figures, a reply that
  never arrived, data erased at the customer's request) carries a
  `HandoffSummaryCode`; the cabinet renders it from its own dictionary
  with the quoted words and the flagged values. `summary` stays: the
  model's own summary (now written in the business's staff language), or
  the code rendered in the staff language.

## 2026-10-03 — calls follow-up: call summaries, missed-call text-backs, Settings → Calls

Spec: `049687053489b322`

- **Added** `GET` and `PUT /v1/businesses/{business_id}/call-settings`
  (owners; `CallSettingsView`, body `CallSettingsRequest`): summaries after
  every call on or off (on by default), text-backs on or off (off by
  default), the WhatsApp utility template name (`^[a-z0-9_]+$`, else 422),
  the SMS fallback; the view adds `is_whatsapp_connected`,
  `is_sms_available` and `template_previews` (the body to register with
  Meta, its parameter `{{1}}` the business name, and what callers read,
  per language of the business). The change is audited.
- **Added** `GET /v1/businesses/{business_id}/text-backs` (owners;
  `limit`, `cursor`; `TextBackPage` of `TextBackView`, newest first): each
  caller who did not get through with `reason`, `source`, the number,
  `language`, `status` (`queued`, `sent`, `failed`, `skipped`),
  `skip_reason`, `channel`, `conversation_id`, `sent_at`, `last_error`.
  Audited as a view of personal data.
- **Added** `GET /v1/telephony/zadarma/notifications?zd_echo=` (Zadarma's
  address check, answers the token as plain text) and
  `POST /v1/telephony/zadarma/notifications` (form body, `Signature`
  header; `PbxCallWebhookOutcome` with `status` `recorded`, `duplicate` or
  `ignored`, `missed_call_id`, `text_back_status`; a wrong or missing
  signature is 401).
- **Changed** `CallView` (conversation card) gains `summaries`
  (`language`, `text`); the post-call webhook also accepts
  `call_initiation_failure` events (a call the voice platform could not
  start becomes a missed call; `status` `recorded` or `duplicate`).

## 2026-10-03 — team inbox: views, assignment, internal notes, quick replies

Spec: `730cfe4d3afda319`

- **Added** `GET /v1/businesses/{business_id}/inbox` (owners and staff,
  `?view=needs_person|requests|mine|unassigned|all`, `channel`, `limit`,
  `cursor`; an unknown view is 422): one keyset page by `last_message_at`
  with the `counts` of the views (`InboxPage`); rows are staff-safe
  (`InboxItemView`: no model costs, tool calls, free-text request details
  or note texts, only `note_count`) and the read is audited per viewer.
- **Added** `GET …/inbox/counts` (`InboxViewCounts`) and
  `GET …/inbox/assignees` (members with their `awaiting_count`).
- **Added** `POST …/conversations/{conversation_id}/assign`
  (`{"assignee_user_id": id|null, "expected_revision"}`): compare and set
  on `assignment_revision`; a stale revision is 409 `assignment_changed`,
  a colleague's conversation for staff 403 `assigned_to_colleague`, a
  non-member 422 `not_a_member` (`ConversationAssignmentView`).
- **Added** `GET` (owners and staff) and `PUT` (owners)
  `…/inbox/settings`: auto-assignment of new handoffs and requests, to
  chosen members or else by workload.
- **Added** `GET·POST …/conversations/{conversation_id}/notes` and
  `DELETE …/notes/{note_id}` (204; the author or an owner, else 403
  `not_note_author`): internal notes, never sent to the model or the
  customer.
- **Added** `GET` (owners and staff), `POST` (201), `PUT` and `DELETE`
  (204) `…/quick-replies[/{quick_reply_id}]` (owners): saved replies with
  one variant per language (422 `unknown_variable` or
  `duplicate_language`, 409 `shortcut_taken` or `too_many_quick_replies`),
  and
  `GET …/conversations/{conversation_id}/quick-replies`: each reply in the
  conversation's language with `{name}`, `{booking_time}` and
  `{business_name}` filled in and `missing_variables`.
- **Changed** the contact export (`ContactRecords`) has `notes`; exported
  conversations carry the assignment fields.

## 2026-10-03 — hosted chat page, share links and QR codes, a better widget

Spec: `7ad2f92ba01caf7a`

- **Added** `GET /v1/businesses/{business_id}/share-links?src=<tag>`
  (owners and staff): the hosted chat page (`/c/{slug}` on the cabinet's
  site; `hosted_chat_url` is null with the gap `not_configured` while
  `CABINET_BASE_URL` is not set) and a link per switched-on channel
  (`wa.me`, `t.me`, `m.me`, `ig.me`, `tel:`), tagged with `?src=` on the
  hosted page and `?ref=` on m.me and ig.me; a channel whose public address
  is not known yet has the gap `reconnect_channel` (`ShareLinksView`). The
  first call gives the business its address (a slug from its name).
- **Added** `PUT /v1/businesses/{business_id}/public-slug` (owners): a new
  address for the hosted chat page; 409 `slug_taken`, 422 `slug_reserved`.
  Older addresses keep leading to the business.
- **Added** `GET /v1/public/chat/{address}` (public, `noindex`, no-store):
  what the hosted chat page needs before the widget loads, by slug or
  business id (`HostedChatView`); an unknown address is 404.
- **Added** `POST /v1/widget/{business_id}/handoff` (public, widget CORS):
  "Talk to a person" for the visitor key in the body; the conversation is handed to staff with the reason
  `customer_request` (`WidgetHandoffView`); 404 when the website chat is
  off, 409 when the business is not live, 429 past its own per-visitor
  limits.
- **Changed** `WidgetConfigView` has `starter_questions` (up to three per
  language from the business's FAQ), `privacy_url` (the business's own
  notice, else the platform's default at `/c/{slug}/privacy`) and
  `contact_links` (the other channels, for the hosted page).
- **Changed** `BusinessLinkKind` has `privacy` (the privacy notice link in
  the profile's links). Profile reads may now return it; it is stored in a
  field of its own so earlier releases can still read the profile.

## 2026-10-03 — knowledge import from the business's website

Spec: `a32037da1580ea8b`

- **Added** `POST /v1/businesses/{business_id}/knowledge/import-website`
  (owners and staff, 202) `{url}`: queues the reading of the business's
  website (`WebsiteImportView`: `id`, `status` queued). The address must be
  a public http(s) address on port 80 or 443: otherwise 422 with
  `reasons[].code` `website_link_invalid` and a detail (`not_http`,
  `credentials_in_url`, `port_not_allowed`, `not_public`). One import at
  a time (409 `website_import_running`), 10 per hour per business (429
  with Retry-After).
- **Added** `GET /v1/businesses/{business_id}/knowledge/import-website/current`
  (owners and staff): `{current}`, the business's latest import with
  `pages_planned`, `pages_read`, `pages_skipped`, `items_found`, `problem`
  (`website_link_invalid`, `website_link_unreachable`,
  `website_link_unreadable`, `website_reader_unavailable`,
  `website_import_interrupted`) with `problem_detail`, and, once `done`,
  `result`: its drafts in the shape of a menu import (`MenuImportResult`;
  confirm and discard them with the menu import endpoints).
- **Added** live event `knowledge_import.progress` (ids: the import id) on
  every step of an import.
- **Changed** (additive) `ImportedMenuItemView.source_page_url`: the page
  of the website a draft was read from.
- **Changed** menu links (`POST …/knowledge/import` with `url`) are read
  through the same SSRF guard: `menu_link_invalid` may now also carry the
  details `credentials_in_url` and `port_not_allowed`, and
  `menu_link_unreadable` the detail `content_encoding:<encoding>`.

## 2026-10-03 — guided launch: one-call creation, setup progress, starter answers, "Apply changes", trial at go-live

Spec: `a4c5c025e7a96d6c`

- **Added** `POST /v1/assistants` ("Create an AI assistant", 201): the
  business with its country's defaults, its guided setup and its niche's
  starter answers (`AssistantCreatedView`); the body is
  `CreateBusinessRequest`.
- **Added** `GET /v1/businesses/{business_id}/setup` (owners and staff,
  `?language=`): the seven setup steps in order with `done`, `skipped`,
  `next` or `todo`, `percent`, `minutes_left`, `next_action`,
  `can_go_live`, `is_live`, `is_complete`, `went_live_at`,
  `trial_ends_at`, `phone_test_links`, `milestones` and the `apply`
  progress (`SetupView`).
- **Added** `PUT` and `DELETE /v1/businesses/{business_id}/setup/skipped-steps/{setup_step}`
  (owners; `offer`, `channels` and `test` only, other steps 422; DELETE
  answers 204) and `POST …/setup/milestones/{kind}/celebrate` (owners and
  staff; a milestone not reached yet is 404).
- **Added** `GET …/setup/starter-answers` and
  `POST …/setup/starter-answers/apply` (owners): the niche's suggestions
  over the country's working week; applying fills only empty sections and
  never suggests prices.
- **Added** `PATCH /v1/businesses/{business_id}/profile` (owners): autosave
  of the fields sent; `expected_updated_at` from an older profile is 409
  `stale_revision`; a patch that changes nothing keeps `updated_at`.
- **Added** `POST` (owners, 202) and `GET` (owners and staff)
  `/v1/businesses/{business_id}/assistant/apply` ("Apply changes"):
  stages `building`, `checking`, `publishing`, `live`,
  `needs_attention` with plain-language reasons and where to fix them
  (`ApplyChangesView`).
- **Changed** `BillingOverview` has `does_trial_start_at_go_live`. The
  free trial starts at the first go-live instead of being started by
  hand: the `subscription_or_trial` go-live check passes with the detail
  `trial_at_go_live`, and a publish refusal of that check now means
  payment is needed.
- **Changed** `POST …/test-chat` builds a draft preview for an owner whose
  latest edits are in no version yet (before the first version too).

## 2026-10-02 — staff notifications: checks, preferences, devices, links

Spec: `1e527cb396131ef6`

- **Added** `GET /v1/businesses/{business_id}/notification-contacts` (owners
  and staff): every staff contact with its `key`, preferences, Telegram
  `telegram_username`, whether this server has a provider for its channel
  (`provider_ready`) and how its latest notification went (`delivery`:
  `pending`, `delivered` or `dead` with `last_error`).
- **Added** `POST /v1/businesses/{business_id}/notification-contacts/{contact_key}/test`
  (owners): sends a test notification at once and answers how it went
  (`NotificationCheckResult`; `is_simulated` when no provider is set
  outside production). At most 5 per contact and hour (429 with
  `Retry-After`).
- **Added** `GET` and `PUT /v1/businesses/{business_id}/notification-preferences`
  (owners and staff, each their own): events (`handoff`, `lead`,
  `booking`) and quiet hours for their devices, the devices, and
  `push_public_key` (None while Web Push is off).
- **Added** `POST /v1/businesses/{business_id}/push-subscriptions` (201,
  turn this device on; the https push services of the browsers only, and
  outside production also a local test push service over http),
  `DELETE …/push-subscriptions/{subscription_id}` (204) and
  `POST …/push-subscriptions/{subscription_id}/test` (own devices only).
- **Added** `GET /v1/businesses/{business_id}/notification-links/{token}`:
  where a signed notification link leads (conversation, request, booking
  with its `booking_date`, or the notification settings); an expired link
  answers `is_expired: true` and names no page, a forged one 404.
- **Changed** `ManagerContactInput` and `ManagerContactView` (in
  `PATCH /v1/businesses/{business_id}` and the business view) gain
  optional `preferences` (events and quiet hours); the view also shows
  `telegram_username` of a chat linked through the platform bot.

## 2026-10-02 — live cabinet: event stream and attention counts

Spec: `761afe1ef683fde3`

- **Added** `GET /v1/businesses/{business_id}/events` (owners and staff):
  Server-Sent Events of what changes in the business. Each event has an
  `id`, a name (`handoff.created`, `handoff.resolved`,
  `conversation.message`, `lead.created`, `lead.changed`,
  `booking.created`, `booking.changed`, `channel.error`,
  `channel.changed`, `autotest.progress`) and `data` with the kind, the
  ids of what changed and the time, never customer text; the client
  reloads what an event names through the usual routes. The stream opens
  with `stream.ready`, sends `stream.resync` when the client should reload
  everything it shows, a heartbeat comment every 20 s, and ends after
  15 minutes; reconnecting with `Last-Event-ID` replays what was missed.
  At most 5 streams per person and API instance (`429` with
  `too_many_live_streams`). Sandbox activity (test chat, autotests) is not
  announced, except autotest progress.
- **Added** `GET /v1/businesses/{business_id}/attention-counts` (owners
  and staff): `open_handoff_count`, `new_lead_count`,
  `unconfirmed_booking_count` (pending bookings that have not started)
  and `channel_error_count`, sandbox left out; indexed counts, no audit
  entry. The cabinet's navigation badges read it.
- **Added** schema `AttentionCounts`.
- **Changed** `GET /v1/businesses/{business_id}/inbox-counts` answers the
  same two counts, now from the same indexed counts; the cabinet reads
  `attention-counts` instead.

## 2026-10-02 — long transcripts page back, lists read one page

Spec: `1572f963cdc6844d`

- **Added** `GET /v1/businesses/{business_id}/conversations/{conversation_id}/messages`
  (owners and staff, audited like the card): earlier messages of a
  conversation, oldest first, `limit` 1 to 200 (default 50) and `cursor`
  from `earlier_messages_cursor` of the card or `next_cursor` of the
  previous page; `next_cursor` is null where the transcript starts.
- **Added** schemas `MessagePage` and `ConversationUsageView`.
- **Changed** `ConversationDetailView`
  (`GET /v1/businesses/{business_id}/conversations/{conversation_id}`):
  `messages` holds the newest 100 messages of the transcript (all of a
  shorter one), oldest first; the new `earlier_messages_cursor` (null when
  nothing is older) pages back through the endpoint above, and the new
  `usage` sums the model tokens and cost of the whole conversation. A
  client that showed the full transcript of a longer conversation pages
  back; `conversation.message_count` still counts every message.
- **Changed** (no shape change) the conversation feed, bookings, leads,
  handoffs, unanswered questions and audit log read one keyset page from
  the database; cursors keep their format. A text search of the feed
  looks through at most the 500 latest conversations per request and goes
  on through `next_cursor`.

## 2026-10-02 — inbox counts for the cabinet's navigation

Spec: `4064d2d88d252e03`

- **Added** `GET /v1/businesses/{business_id}/inbox-counts` (owners and
  staff): `open_handoff_count` (handoffs nobody has resolved) and
  `new_lead_count` (requests still `new`), sandbox activity left out. The
  cabinet shows them as badges on Messages and polls them; they are counts
  only, so a read writes no audit entry (unlike the handoff and lead
  lists).
- **Added** schema `InboxCounts`.
- **Changed** `POST /v1/widget/errors` documents the standard `ErrorBody`
  errors (`401` … `502`) like every other operation; it still answers only
  `204`, `413`, `422` and `429`.

## 2026-10-02 — login abuse protection, body limits and security headers

Spec: `15dd0984bdea39f3`

- **Added** `turnstile_token` to `StartOtpLoginRequest`
  (`POST /v1/auth/otp/start`): the answer of the Cloudflare Turnstile
  check. A risky code request (a phone or e-mail of no verified user, a
  busy client address, half a platform cap used, a high-risk country)
  answers 403 `access_denied` with the reason `challenge_required`, whose
  details hold the widget's site key, while the check is on; the client
  shows the check and sends the request again with its token. High-cost
  numbers (premium rate, shared cost, satellite) answer 422.
- **Changed** `POST /v1/auth/otp/verify` answers 429 `rate_limited` with
  `Retry-After` after 20 checks from one client network or 10 checks of
  one challenge in ten minutes.
- **Added** `payload_too_large` to `ApiErrorCode`: every route answers 413
  with it when the request body is over the route's limit (256 KB; 1 MB
  for platform webhooks, 5 MB for the post-call report, 21 MB for a menu
  import). `MenuImportRequest.data_base64` has a `maxLength` (a 15 MB file
  in base64).
- **Changed** every answer carries `X-Content-Type-Options`,
  `Referrer-Policy`, `X-Frame-Options` and a `frame-ancestors 'none'`
  policy; `/v1/*` answers without their own caching rule are `no-store`;
  production sends HSTS and no longer serves `/docs`, `/redoc` and
  `/openapi.json`.

## 2026-10-02 — one error contract, DELETE answers 204

Spec: `8e2480c367937ab3`

Every failure is an `ErrorBody` now, also the framework's own refusals,
and the description says so, so the cabinet's generated client types its
errors. The cabinet changes in the same pull request; the frozen widget and
platform routes keep their success answers (platforms read only the
status of an error). The pull request carries the `api-breaking` label for
the DELETE and validation-body changes below.

- **Changed** every operation documents `401`, `403`, `404`, `409`, `422`,
  `429` and `502` as `ErrorBody` (`{"error", "message", "reasons"?}`); the
  schemas `HTTPValidationError` and `ValidationError` are gone (the API
  never sent them for request bodies).
- **Breaking** a missing or malformed query parameter or header answers
  `422` `ErrorBody` with `error: "validation_failed"` and one reason per
  field (`code` `missing` or `invalid`, `details: ["query.country_code"]`)
  instead of FastAPI's `{"detail": [...]}`. Migration path: read
  `reasons` (the cabinet's `web/src/api/errors.ts` does).
- **Changed** an unknown route (`404`) or method (`405`) answers
  `ErrorBody` (`not_found`, `validation_failed`) instead of
  `{"detail": "..."}`; a range outside a call recording answers `416` with
  an `ErrorBody`.
- **Breaking** every DELETE answers `204 No Content`:
  `DELETE /v1/businesses/{business_id}/members/{user_id}` (was the
  business), `.../contacts/{contact_id}` (was the erasure counts),
  `.../channels/{channel}` (was the channel),
  `.../knowledge/import/{batch_id}` (was the discarded item ids) and
  `.../integrations/google-calendar` (was `was_connected`). Migration
  path: read the resource again (`GET` the business, the channels, the
  calendar status); the schemas `ContactErasureResult`,
  `DiscardedImportBatch` and `CalendarDisconnectResult` are gone.

## 2026-10-02 — widget error beacon, readiness

Spec: `60e48c140683bbc4`

- **Added** `POST /v1/widget/errors` (public, CORS for any site, like the
  other widget routes): the website widget reports an error of its own
  code — `kind`, `phase`, optional `business_id`, `error_name`, `line`,
  `column` and `status_code`, never a message text — and gets `204`; a
  client network, a business or the platform reporting too many gets
  `429` with `Retry-After`.
- **Added** `GET /readyz` (not in the description, like `GET /healthz`):
  `200` with `"status": "ready"` when the database answers, every
  migration of the build is applied and a connection is free, else `503`;
  the body names each check and the age of the freshest worker heartbeat.
- **Changed** `POST /v1/voice/tools/{tool_name}` answers within 8 s: a
  tool still running then gives the agent an `{"error": ...}` result to
  say to the caller (the tool itself finishes in the background).

## 2026-10-02 — inbox and outbox for customer messages

Spec: `8bf6a7c2e210906f`

The platform webhooks answer as soon as the delivery is stored in the
inbox; the background worker answers the customer later. Telegram, Meta
and ElevenLabs read only the HTTP status of these answers, and the cabinet
does not call these routes, so no client has to change. The two new enum
values below are reported by `oasdiff` as breaking (new value of a
response enum on a frozen route): the pull request carries the
`api-breaking` label.

- **Added** `queued` and `duplicates` to `ChannelWebhookOutcome`
  (`POST /v1/channels/telegram/{channel_id}/webhook`,
  `POST /v1/channels/meta/webhook`): new customer messages stored for the
  worker, and messages the platform delivered before.
- **Changed** `answered` and `silenced` of `ChannelWebhookOutcome` are
  always `0` now (replies are sent by the worker, not within the request);
  `failed` counts messages that could not be stored.
- **Breaking** `PlatformBotCommandResult` gains `queued`
  (`POST /v1/channels/telegram-platform/webhook`): the staff message is
  stored and the worker answers it. Migration path: none needed, Telegram
  ignores the body.
- **Breaking** `PostCallEventStatus` gains `queued`
  (`POST /v1/voice/webhooks/post-call`): the report is stored and the
  worker files the call; a repeated delivery of the same report answers
  `duplicate`. Migration path: none needed, ElevenLabs ignores the body.
- **Changed** (additive) `CallDocument` (the `calls` of a contact's data
  export) has `schema_version` `2`: stored calls carry the after-call
  check fields (older calls are read as version 2 with them empty).

## 2026-10-02 — phone instruction and call checks

Spec: `339e62eb0e3edb17`

- **Changed** (additive) `AssistantVersionDetails` (`GET
  /v1/businesses/{business_id}/assistant-versions/{version_id}` and the
  assemble answer) has `phone_prompt_text`: the instruction the phone
  assistant speaks from (spoken prices and hours, no links); `null` for a
  version without voice or one assembled before it existed.
- **Changed** (additive) `CallView` (the `calls` of `GET
  /v1/businesses/{business_id}/conversations/{conversation_id}`) has
  `guard_verdict` (`clean`, `flagged`, `handed_off`; `null` for a call not
  checked) and `unverified_values`: what the after-call check found in the
  values the phone assistant said.
- **Added** schema `CallGuardVerdict`.

## 2026-10-02 — background job queue

Spec: `f4380cc473533ee9`

- **Added** `GET /v1/admin/jobs` (platform admins only): background jobs,
  the most recently changed first, paged with `limit` and `cursor` and
  filtered by `status` (`pending`, `running`, `done`, `dead`, `discarded`)
  and `name`. Job payloads are never returned.
- **Added** `POST /v1/admin/jobs/{job_id}/retry` (a dead or discarded job
  runs again) and `POST /v1/admin/jobs/{job_id}/discard` (a dead or waiting
  job is dropped). Both answer the job and the id of the audit entry that
  records the action; `409` when the job is in another state, `404` for an
  unknown job, `403` for anyone but a platform admin.
- **Added** schemas `QueuedJobView`, `QueuedJobPage`, `QueuedJobStatus`,
  `JobLane` and `AdminJobActionResult`.

## 2026-10-02

Spec: `1052b4e91d0ed103`

- **Changed** The JSON bodies of `POST /v1/businesses/{business_id}/billing/trial`,
  `.../billing/plan` and `.../billing/checkout` are described as optional
  (`requestBody.required: false`). The API already treated an empty body as
  all defaults; the description now says so.
- **Changed** Request bodies of the knowledge, resource and profile routes
  are read by the same parser as all other routes: an empty body is
  refused with `422 validation_failed` and validation messages no longer
  repeat submitted values; malformed path ids answer `404` with
  "<Entity> was not found." and invalid `?language=` values answer `422`
  without echoing the value. Shapes and status codes are unchanged.

## 2026-10-01 — `/v1` baseline

Spec: `bd53326db97cc3cc`

- **Added** The first described version of `/v1`: authentication with
  one-time codes, businesses and team, profile wizard, knowledge base,
  resources and schedules, assistant versions and autotests, conversations,
  bookings, leads, handoffs, unanswered questions, dashboard, channels and
  the website widget, billing and Flitt payments, compliance (DPA, audit
  log, customer data requests), catalog and platform administration.
