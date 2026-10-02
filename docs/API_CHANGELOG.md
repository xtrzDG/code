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

## 2026-10-02 — inbox counts for the cabinet's navigation

Spec: `f5a7d64f13ad3ace`

- **Added** `GET /v1/businesses/{business_id}/inbox-counts` (owners and
  staff): `open_handoff_count` (handoffs nobody has resolved) and
  `new_lead_count` (requests still `new`), sandbox activity left out. The
  cabinet shows them as badges on Messages and polls them; they are counts
  only, so a read writes no audit entry (unlike the handoff and lead
  lists).
- **Added** schema `InboxCounts`.

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
