# API versioning and change policy

The HTTP API has three kinds of clients, and each sets its own limit on
change:

| Client | Routes | Who updates it | Rule |
| --- | --- | --- | --- |
| Owner cabinet (`web/`) | `/v1/...` (cabinet, catalog, auth, admin) | we, in the same pull request | additive within `/v1` |
| Website widget | `/widget.js`, `/widget/demo`, `/v1/widget/{business_id}/config`, `/v1/widget/{business_id}/messages` | nobody: the snippet is pasted on customers' sites and cached by browsers and CDNs | **frozen** |
| Integrations (Zapier, customers' scripts) | `/v1/public-api/*` (tag `public-api`) and the webhook requests we send | customers, at their own pace | **frozen** (below) |
| Platforms | `/v1/channels/telegram/{channel_id}/webhook`, `/v1/channels/telegram-platform/webhook`, `/v1/channels/meta/webhook`, `/v1/payments/flitt/webhook`, `/v1/voice/tools/{tool_name}`, `/v1/voice/webhooks/*`, `/v1/integrations/google-calendar/callback` | registered once at Telegram, Meta, Flitt, ElevenLabs and Google | **frozen** |

`web/openapi.json` is the contract. It is exported from the code
(`cd web && npm run gen:api`), the cabinet's typed client
(`web/src/api/schema.d.ts`) is generated from it, and CI checks that both
are current.

## Within `/v1`: additive changes only

Allowed without a new version:

- a new route, a new optional query parameter, a new optional request field;
- a new response field (clients ignore fields they do not know);
- a request field or body that becomes optional, a limit that becomes looser;
- a new value of an enum **in a request**.

Breaking, and therefore not allowed in `/v1`:

- removing or renaming a route, a field or an enum value;
- making an optional request field or body required, tightening a limit;
- changing a field's type, format, unit (microseconds, minor units) or meaning;
- a new value of an enum **in a response** that existing clients cannot
  display (add it behind a request parameter, or as a new field);
- changing status codes or error `code`s that clients branch on.

The `API contract` workflow (`.github/workflows/api-contract.yml`) runs
`oasdiff breaking <merge-base>/web/openapi.json web/openapi.json --fail-on ERR`
on every pull request. A deliberate break, agreed with every client, is let
through only by the `api-breaking` label, and must be recorded in
`docs/API_CHANGELOG.md` together with the migration path.

## Operation names

Every operation has a tag and an `operationId` of the form
`<tag>_<route function name>` in snake_case (`admin_list_clients`,
`operations_post_booking`), made by `app/gateways/http/operation_ids.py`.
SDK generators turn these ids into method names, so an id is a public name:
renaming a route function or moving a route under another tag is a
breaking change. The oasdiff gate treats a changed id as an error
(`.github/oasdiff-severity-levels.txt`), and
`tests/platform/test_api_contract.py` checks that every id is unique and
snake_case.

## Idempotency keys

A creating request may carry `Idempotency-Key: <a value you choose once per
action>` (1 to 255 visible ASCII characters; a UUID is best) and send the
same key again on every retry of that action. The operations that honour
it document the header:

- `POST /v1/assistants` (create an assistant);
- `POST /v1/businesses/{business_id}/bookings`;
- `POST /v1/businesses/{business_id}/conversations/{conversation_id}/messages`
  (a staff message);
- `POST /v1/businesses/{business_id}/billing/checkout` and `…/subscribe`.
- `POST /v1/public-api/bookings`, `POST /v1/public-api/leads` and
  `POST /v1/public-api/webhooks` (the public API; the keys belong to the
  user who created the API key).

There is no creating `POST` for leads (the assistant records them), so
they need no key. Other operations ignore the header. The rules:

| The request | The answer |
| --- | --- |
| no key | runs as always |
| a new key | runs; a successful (2xx) answer is kept for 24 hours |
| the same key, method, path and body (JSON compared by content, not spacing or key order) after a success | the kept answer again, status and body as first sent, with `Idempotent-Replayed: true`; nothing runs twice |
| the same key with another path or body | 409 `conflict`, reason `idempotency_key_reused` |
| the same key while the first request still runs | 409 `conflict`, reason `in_progress`: retry a bit later |
| the same key after a refused (4xx) or failed (5xx) request | runs again: a failure frees its key |
| an invalid key | 422 `validation_failed`, details `header.Idempotency-Key` |

Keys belong to the signed-in user: two users never meet on a key. They are
stored in `idempotency_keys` (migration 1174) under an id derived from the
user and the key, with a SHA-256 fingerprint of the request (not the body
itself) and, after a success, the answer; the hourly
`purge_idempotency_keys` job deletes them after their day (an audited
retention purge). A request holds its key for at most 5 minutes: a key left
by a process that died mid-request can be used again after that. An answer
larger than 256 KiB is sent but not kept, so its retry runs again. The
cabinet sends one key per user action (`web/src/api/idempotencyKey.ts`) and
the same key when it sends the action again after a step-up confirmation.

Limits: the key guards against a retry, not against two different actions;
and when a process dies after the creation but before the answer was kept,
the next retry after the lease runs again.

## ETag and If-Match

`GET` and `PATCH /v1/businesses/{business_id}` (the business settings)
answer the business revision as a strong `ETag` (`"7"`), the same number as
the body's `revision`. A `PATCH` with `If-Match: "7"` applies only while the
stored revision is still 7; otherwise nothing changes and the answer is
`412 Precondition Failed` with `error: conflict` and the reason
`precondition_failed`, whose details carry the current revision. A save by
someone else between reading and writing is refused the same way.
`If-Match: *` accepts any revision; a list (`"6", "7"`) accepts any of its
tags; weak tags (`W/"7"`) never match (strong comparison). Without
`If-Match`, the body's `expected_revision` remains the same check answered
with 409 `stale_revision` (the cabinet uses it). The ETag names the
business revision for writes; it is not a cache validator (no
`If-None-Match`/304).

## The public API and webhooks: a frozen contract

`/v1/public-api/*` (tag `public-api`) is the API customers call with an API
key (Settings → Integrations → API keys, `Authorization: Bearer awk_…`),
and the webhook requests we send are a contract their receivers parse. Both
are frozen like the widget routes: nothing is removed, renamed or retyped,
and no response gains a value of an enum an existing client cannot handle.
Allowed: a new route, a new optional field in a request, a new field in a
response or an event's `data`, a new event type (sent only to endpoints that
subscribe to it by name). Anything else is `/v2/public-api`, run next to
`/v1` for at least 12 months. The cabinet's own routes for keys and webhooks
(`/v1/businesses/{business_id}/api-keys`, `…/webhooks`,
`…/webhook-deliveries`, tags `api-keys` and `webhooks`) follow the ordinary
`/v1` rule.

**Keys.** A key belongs to one business; it is shown once and stored as a
scrypt digest salted with its public prefix (compared in constant time). Its scopes (`bookings:read`, `bookings:write`,
`leads:read`, `leads:write`, `contacts:read`, `conversations:read`,
`webhooks:manage`) decide what it may do: a missing scope is 403
`access_denied` with the reason `missing_scope`; a record of another business is
404. A key makes at most `PUBLIC_API_REQUESTS_PER_MINUTE` requests a minute
(429 with `Retry-After`); every read and write is audited under the key. A
client network that sent 60 keys that are not valid within a minute gets
429 with `Retry-After` before any further key is checked.

| Route | Scope |
| --- | --- |
| `GET /v1/public-api/me` | any: the key, its scopes and its business |
| `GET /v1/public-api/bookings`, `…/bookings/{id}` | `bookings:read` |
| `POST /v1/public-api/bookings` | `bookings:write` (201; capacity and hours enforced) |
| `GET /v1/public-api/leads`, `…/leads/{id}` | `leads:read` |
| `POST /v1/public-api/leads` | `leads:write` (201) |
| `GET /v1/public-api/contacts`, `…/contacts/{id}` | `contacts:read` |
| `GET /v1/public-api/conversations`, `…/conversations/{id}` | `conversations:read` (one with its messages) |
| `POST /v1/public-api/webhooks`, `DELETE …/webhooks/{id}` | `webhooks:manage` (REST hooks: Zapier subscribes and unsubscribes) |

Lists are newest first and take `?limit` (1 to 200) and the `cursor` of
the previous page's `next_cursor`. Times are ISO 8601 with the business's
offset. The two creating `POST`s honour `Idempotency-Key` (rules above;
keys belong to the user who created the API key). Sandbox (test chat)
records are never returned.

**Webhook requests.** An endpoint (a public `https` address; private,
loopback and link-local addresses are refused before every attempt, and
redirects are not followed) receives one `POST` per event it subscribed to:

```http
POST /your/hook HTTP/1.1
Content-Type: application/json
Workshop-Event-Id: event_…
Workshop-Event-Type: booking.created
Workshop-Delivery-Id: webhook_delivery_…
Workshop-Signature: t=1791331200,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd

{"id": "event_…", "type": "booking.created", "created_at": "2026-10-06T21:00:00+04:00",
 "business_id": "business_…", "data": { …the record as the public API returns it… }}
```

Event types: `booking.created`, `booking.updated`, `booking.cancelled`,
`lead.created`, `lead.updated`, `handoff.created`, `handoff.resolved`,
`conversation.started`, `call.finished`, and `webhook.test` (the owner's
"Send test event"). Bookings, leads, conversations and calls carry the
`acquisition_source` that brought the customer, bookings their `value`.

To verify a request, take `t` and `v1` from `Workshop-Signature`, compute
HMAC-SHA256 over `<t>.<raw body>` keyed with the endpoint's whole signing
secret (`whsec_…`, shown once when the endpoint is created or its secret
rotated), compare in constant time, and refuse a `t` more than 5 minutes
from your clock. Answer 2xx within 10 seconds; the same `Workshop-Event-Id`
may arrive more than once and events may arrive out of order.

A failed attempt (a network error, a timeout, 3xx, 4xx or 5xx) is tried
again after about 30 s, 2 min, 10 min, 30 min, 1 h, 2 h, 4 h, 6 h and
8 h (±20 %), for at most 24 hours from the event. After
`WEBHOOK_DISABLE_AFTER_FAILURES` failed attempts in a row the endpoint is
switched off (Settings → Integrations shows it, and the owner turns it
on again); an answer of 410 Gone switches it off
at once (and removes a REST-hook subscription). The delivery log in the
cabinet keeps every delivery for 30 days, and a failed one can be sent
again from there.

## Deprecation

A route or field that will go away in a later version stays working for at
least 6 months (frozen routes: until no client uses it). While it is
deprecated:

1. The OpenAPI description marks it (`deprecated=True` on the route, or
   `Field(deprecated=True)` on a field), so the generated client shows it.
2. Responses of a deprecated route carry the headers of RFC 9745 and
   RFC 8594, and a link to the replacement:

   ```http
   Deprecation: @1790812800
   Sunset: Thu, 01 Apr 2027 00:00:00 GMT
   Link: </v2/...>; rel="successor-version", </docs/API_CHANGELOG.md>; rel="deprecation"
   ```

3. The entry in `docs/API_CHANGELOG.md` names the sunset date and the
   replacement, and the access log is watched for remaining callers before
   the sunset.

Removal happens only in a new major version (`/v2/...`), which runs next to
`/v1` until `/v1`'s sunset date.

## Every change is recorded

Each pull request that changes `web/openapi.json` adds an entry on top of
`docs/API_CHANGELOG.md` with the date, what changed for clients, and the
`Spec:` fingerprint of the new description (the first 16 hex digits of its
SHA-256, `sha256sum web/openapi.json | cut -c1-16`).
`tests/platform/test_api_changelog.py` fails until the newest entry names the
committed description.
