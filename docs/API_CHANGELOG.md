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
