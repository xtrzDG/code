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

## 2026-10-03 — widget messages are answered by the worker

Spec: `74e937607f65fc64`

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
