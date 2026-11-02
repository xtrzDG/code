# Render outage

**Alerts:** the uptime monitor's `/readyz`, `/healthz/pipeline` and
`/status` checks all fail at once; Sentry goes quiet (nothing runs to report);
the platform alerts stop (the workers and the API's watchdog run on Render
too). A Render incident on https://status.render.com for Frankfurt.

Render hosts everything in one region (`render.yaml`, `region: frankfurt`):
the API, the workers, the cabinet, `workshop-db` and the backup cron. A
regional outage is SEV1: no business gets answers in any channel.

## What already happens by itself

- Meta and Telegram retry their webhooks for hours, so customers'
  messages arrive late, not never.
- Calls: the voice agent runs at ElevenLabs, but it reaches our API for
  the call's set-up and for every tool, and the voice fallback of rented
  numbers is an API route too; expect calls to fail or to end without a
  booking.
- Jobs live in the database: once it is back, the workers pick up where
  they stopped; nothing is sent twice (outbox ids are idempotent).

## Check

1. Is it Render or us? https://status.render.com for Frankfurt; the
   dashboard's events of `workshop-api`, `workshop-worker` and
   `workshop-db`. A deploy of ours in the last hour is
   [bad-deploy](bad-deploy.md) instead.
2. Which part: the web services (API, cabinet), the workers, or the
   database ([database-failover](database-failover.md))?
3. Open a ticket with Render at once and note its number.

## Mitigate

- Post the status announcement from outside: the uptime monitor's public
  page (the cabinet's `/status` is down with everything else), and an
  e-mail to owners from the support mailbox after 30 minutes (SEV1
  schedule, `docs/operations/incident.md`).
- Tell owners to switch their call forwarding off and answer the phone
  themselves until the notice that service is back.

## Recover elsewhere (outage longer than 4 hours)

The RTO of `docs/operations/backup-restore.md` applies; the founder decides.

1. Create a Postgres 16 with pgvector in another EU region or provider and
   restore the newest off-site backup into it (`workshop restore-check
   --keep-database`, "Restore runbook" of `docs/operations/backup-restore.md`).
   Data written since that night's backup is lost unless Render's own copy
   comes back: say so in the owners' notice.
2. Run the image (`Dockerfile`) as `workshop api` and `workshop worker`
   with the env group's variables (`docs/security/secrets-inventory.md`
   names every secret and its store) and the cabinet (`web/Dockerfile`).
3. Point the same DNS names at the new hosts ([dns-outage](dns-outage.md),
   "Moving a name"): the webhooks of Meta, Telegram, the voice platform,
   Twilio and the PSPs name those hosts, so they keep working once the
   names resolve to the new ones.
4. When Render is back, do not run both: stop the Render services before
   the DNS moves back, and restore the newer database into Render.

## Afterwards

- Postmortem (SEV1). Was the backup's age (RPO) acceptable? Should the
  database get a high-availability standby or a second region?
