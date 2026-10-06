# API versioning and change policy

The HTTP API has three kinds of clients, and each sets its own limit on
change:

| Client | Routes | Who updates it | Rule |
| --- | --- | --- | --- |
| Owner cabinet (`web/`) | `/v1/...` (cabinet, catalog, auth, admin) | we, in the same pull request | additive within `/v1` |
| Website widget | `/widget.js`, `/widget/demo`, `/v1/widget/{business_id}/config`, `/v1/widget/{business_id}/messages` | nobody: the snippet is pasted on customers' sites and cached by browsers and CDNs | **frozen** |
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
