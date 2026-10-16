# Delivery failures (the outbox)

**Alert:** `outbound_failures` (SEV2): over 10% of the outbox messages
queued in the last hour that settled died, with at least 20 settled.

## How it shows

- Dead letters of `deliver_outbound` on `/admin/system`; channels in
  ERROR when a provider refused the channel's credential.
- Owners: "my customer says they got no answer", staff notifications
  missing.

## Check

1. Which channel? The dead letters' errors name the provider and its
   code. Most often: WhatsApp outside the 24-hour window without an
   approved template (131047), a paused template, an invalid number, a
   blocked bot (Telegram 403), or a provider outage.
2. One business or many? One: its channel or its customers. Many: the
   provider ([meta-outage](meta-outage.md),
   [telegram-outage](telegram-outage.md)) or our last deploy
   ([bad-deploy](bad-deploy.md)).
3. Staff notifications by e-mail or SMS: `SMTP_*` / `TWILIO_*` errors in
   the log (a revoked key, a full mailbox, Twilio geo permissions).

## Mitigate

- Provider outage: wait; the outbox retries with backoff.
- A channel's credential: the owner connects it again (Channels page).
- A template: fix and resubmit it in WhatsApp Manager; reminders and
  staff notifications use `WHATSAPP_REMINDER_TEMPLATE` and
  `WHATSAPP_NOTIFICATION_TEMPLATE`.
- A customer who blocked the bot: nothing to fix; discard.

## Fix and recover

- Retry the dead letters once the cause is gone (each message is sent once:
  outbox ids are idempotent). Discard customer replies older than a day.

## Afterwards

- If a template or a provider setting was the cause, add it to
  `docs/LAUNCH.md` so the next setup avoids it.
- Game day: `tests/chaos/test_meta_blackhole_game_day.py` black-holes
  Meta's Graph API host under twenty WhatsApp customers: every reply is
  tried eight times with backoff and fails for good, `outbound_failures`
  fires at the next five-minute check and /status shows the messengers
  degraded; once Meta answers new replies go out and the alert resolves
  after the hour. (The dead replies stay dead letters: retry them here.)
