# Database restart or failover

**Alerts:** the external uptime monitor on `GET /readyz` (503:
`checks.database.failure` is `unreachable` or `timeout`), `worker_down`
and `inbound_backlog` from the API's watchdog when the outage outlasts
five minutes, Sentry `ExternalServiceError` from the Postgres pool.

`workshop-db` is one Render Postgres 16 (`render.yaml`). A restart
(maintenance, a plan change, a crash) takes it away for one to a few
minutes; a plan with a high-availability standby fails over to it in
about the same time; without one, a lost instance is restored from the
latest backup ([backup-restore](../backup-restore.md), path B).

## How it shows

- API: `/readyz` 503; requests that need the database fail with 502
  `external_service_error` (Sentry has the pool's error); the cabinet
  shows its "cannot reach the platform" state.
- Workers: lanes log `Job job_queue failed: ...` and keep polling; failed
  periodic runs are tried again in their next period; no job is lost
  (they live in the database).
- Webhooks from Meta and Telegram get 5xx: both providers retry for hours,
  so customer messages arrive late, not never.

## Check

1. Render → `workshop-db` → Events: a restart, maintenance, a failover,
   disk full (the size per table is on `/admin/system`).
2. Render status page (status.render.com): a regional incident in
   Frankfurt.
3. Connections: Render → Metrics → connections against the plan's limit
   (`../capacity.md`, "Connection budget"). A full pool looks like an
   outage from the API's side.

## Mitigate

- **Restart or failover in progress:** wait. The pools reconnect by
  themselves (each connection is checked before use, broken ones are
  replaced), the workers resume claiming, and the API's `/readyz` turns
  200 on the next probe. Do not restart the services in a loop: each
  restart drops the requests in flight.
- **Longer than 15 minutes:** post an `outage` announcement for every
  component (it shows once the database is back, and in the banner);
  tell owners per `../incident.md`.
- **Connections exhausted:** restart the service that leaks (the one with
  the most connections in `pg_stat_activity`), then look for the cause.
- **Instance lost, no standby:** restore the latest backup into a new
  database (path B of `../backup-restore.md`), point `DATABASE_URL` at it
  and redeploy; the restore drill's measured time is the expected RTO.

## Fix and recover

- Retry dead letters that ran out of attempts during the outage
  (`/admin/system` → Dead letters), customer replies first.
- The webhooks the providers retried arrive by themselves; the inbox's
  sweeper (`sweep_stale_inbound_events`, every five minutes) re-queues
  events accepted but not processed.
- `worker_down` and `inbound_backlog` resolve on the watchdog's next look.

## Afterwards

- Postmortem with the minutes of the outage against both budgets.
- Game day: `tests/chaos/test_postgres_restart_game_day.py` restarts the
  test database under both processes and checks the recovery.
