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
