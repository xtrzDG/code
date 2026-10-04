# Telegram outage

**Alerts:** `outbound_failures` (bot replies or staff notifications die),
owners reporting that their Telegram bot is silent. Platform alerts
themselves may not arrive in the Telegram ops chat: keep
`PLATFORM_ALERT_EMAILS` set so the team still hears.

## How it shows

- Dead letters of `deliver_outbound` with Telegram 5xx or timeouts; no
  `process_inbound_message` jobs for Telegram channels.
- Staff notifications through the platform bot
  (`TELEGRAM_PLATFORM_BOT_TOKEN`) queue up as retries.

## Check

1. Is api.telegram.org answering? (`curl -sS https://api.telegram.org`
   from any machine; status pages: downdetector, @BotNews.)
2. One bot or all? A business's bot token revoked by its owner in
   @BotFather shows as that channel in ERROR (401) on `/admin/system`.
3. The platform bot: Telegram → @BotFather → the bot is still there, the
   token unchanged.

## Mitigate

- **Telegram down:** Telegram keeps undelivered webhook updates for 24 h
  and retries them; replies retry in the outbox. Tell affected owners
  that staff notifications come late and that e-mail/SMS contacts still
  work (Settings → Notifications).
- **A business's bot token revoked:** the owner pastes the new token
  (Channels → Telegram); the webhook is registered again.
- **The platform bot's token leaked or revoked:** create a new token in
  @BotFather, set `TELEGRAM_PLATFORM_BOT_TOKEN` on `workshop-api`,
  redeploy API and worker. Staff linked by "/start <code>" stay linked.

## Fix and recover

- Retry dead letters of `deliver_outbound` and `send_platform_alert` once
  Telegram answers.

## Afterwards

- Postmortem if it lasted over an hour or owners missed bookings.
