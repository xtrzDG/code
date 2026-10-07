# Zapier app (scaffold)

A [Zapier Platform CLI](https://github.com/zapier/zapier-platform) app on
top of the public API (`/v1/public-api/*`, frozen; see
[docs/api-versioning.md](../../docs/api-versioning.md)).

| Kind | Key | What |
| --- | --- | --- |
| Trigger (REST hook) | `new_booking`, `updated_booking`, `cancelled_booking` | `booking.created`, `booking.updated`, `booking.cancelled` |
| Trigger (REST hook) | `new_lead`, `updated_lead` | `lead.created`, `lead.updated` |
| Trigger (REST hook) | `new_handoff`, `resolved_handoff` | `handoff.created`, `handoff.resolved` |
| Trigger (REST hook) | `new_conversation`, `finished_call` | `conversation.started`, `call.finished` |
| Action | `create_booking` | `POST /v1/public-api/bookings` |
| Action | `create_lead` | `POST /v1/public-api/leads` |

- **Authentication**: an API key (Settings → Integrations → API keys),
  sent as `Authorization: Bearer awk_…`; the connection is tested with
  `GET /v1/public-api/me` and named after the business and the key.
- **Triggers** subscribe Zapier's hook URL with `POST /v1/public-api/webhooks`
  when a Zap is turned on (the key needs `webhooks:manage`) and remove it
  with `DELETE /v1/public-api/webhooks/{id}` when it is turned off. Every
  request is checked against the subscription's signing secret
  (`Workshop-Signature`, `lib/signature.js`, at most five minutes old); one
  that cannot be checked (no secret, no raw body, no signature) is refused,
  never passed on. The editor's test step reads
  recent records through the list routes where there is one (it needs the
  read scope); handoffs and calls use the built-in sample.
- **Actions** send an `Idempotency-Key` made from the Zap and its input,
  so a step that Zapier retries does not create the record twice.

## Run the tests

```sh
cd integrations/zapier
npm test        # node --test, no network and no dependencies needed
```

## Publish

Publishing needs a Zapier developer account, which this repository does
not have yet; nothing here has been pushed to Zapier.

```sh
npm install -g zapier-platform-cli
cd integrations/zapier
npm install
zapier login
zapier register "Assistant Workshop"     # once; writes .zapierapprc
zapier env:set 1.0.0 WORKSHOP_API_URL=https://<the API's public address>
zapier validate
zapier push
```

`platformVersion` follows the pinned `zapier-platform-core` in
`package.json`; raise both together. `overrides` holds `form-data` at
4.0.6: core 19.1.0 pins 4.0.5, which has a CRLF injection in multipart
field names (GHSA-hmw2-7cc7-3qxx); drop the override once the core's own
pin is 4.0.6 or later (`npm audit --omit=dev` after `npm install`). A new trigger or field is fine at any
time; renaming a key breaks existing Zaps (it is the same rule as the
public API's).
