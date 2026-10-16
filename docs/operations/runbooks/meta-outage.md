# Meta outage: WhatsApp, Messenger, Instagram

**Alerts:** `outbound_failures` (replies die at Meta), channels in ERROR on
`/admin/system`, owners reporting silence in WhatsApp.

## How it shows

- Outbox dead letters of `deliver_outbound` for WhatsApp, Messenger or
  Instagram; `last_error` names Meta's code.
- Channels in ERROR with "Meta rejected the access token (190)": that
  business's token, not Meta.
- No webhooks at all for minutes: incoming messages from Meta stop.

## Check

1. metastatus.com (WhatsApp Business API, Messenger Platform).
2. One business or all? The channels-in-ERROR list and the dead letters by
   job show it. One business: its token or its number's quality rating.
3. Meta error codes: 190 (token expired or revoked), 131047 (outside the
   24-hour window; the template path should have been used), 131026
   (not a WhatsApp number), 130429 / 131056 (throughput), 368 (the number
   is restricted by Meta's policy).

## Mitigate

- **Meta down:** nothing to switch; incoming messages are queued by Meta
  and arrive later, outgoing replies retry. Tell owners (template in
  `../incident.md`): messages are kept, nothing is lost.
- **One business's token:** the owner connects the channel again on the
  Channels page with a new token. For the platform's own number
  (`WHATSAPP_SYSTEM_USER_TOKEN`), create a new system-user token in Meta
  Business Settings and set it on `workshop-api`; redeploy.
- **Tokens running out:** `/admin/system` lists Meta tokens that run out
  within 14 days; ask those owners to reconnect before they do. The hourly
  `check_channel_credentials` job asks Meta (`debug_token`, with
  `META_APP_ID` and `META_APP_SECRET`) about each token once a day; a
  token Meta no longer accepts shows as expired.
- **Throughput:** Meta raises messaging limits by quality and volume; the
  outbox retries with backoff, keep it running.

## Fix and recover

- Retry the dead letters of `deliver_outbound` once Meta answers again;
  the outbox sends each message once (idempotent per message).
- Channels left in ERROR clear when the owner reconnects or the next
  delivery succeeds.

## Afterwards

- If a template was rejected or paused, fix it in WhatsApp Manager and in
  `WHATSAPP_NOTIFICATION_TEMPLATE` / `WHATSAPP_REMINDER_TEMPLATE`.
- Postmortem for SEV2 if owners noticed.
- Game day: `tests/chaos/test_meta_blackhole_game_day.py` (Meta's host
  takes requests and never answers; see
  [delivery-failures](delivery-failures.md)).
