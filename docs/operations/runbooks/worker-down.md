# No worker answers (worker down)

**Alerts:** `worker_down` (SEV1): no worker wrote its pulse for five
minutes; `inbound_backlog` (SEV2): a customer message waited over 120 s.
Both come from the **API's pipeline watchdog**, not from a worker: one
API process leads it (a lease in `platform_monitors`, renewed every
minute), looks every `PIPELINE_WATCHDOG_SECONDS` (60) and sends the alert
straight through the platform bot and SMTP, without the job queue the
dead workers would have to drain. The external uptime monitor sees the
same reading on **`GET /healthz/pipeline`** (503) while `GET /readyz`
stays 200.

## How it shows

- Telegram/e-mail: `[SEV1] FIRING: No worker answers`, sent once per
  episode (again after `PLATFORM_ALERT_COOLDOWN_MINUTES`).
- `GET /healthz/pipeline` → 503 with
  `checks.worker.pulse_age_seconds` and `checks.inbound.oldest_wait_seconds`.
- `/status`: website chat, WhatsApp/Instagram/Messenger and Telegram show
  an outage; once the alert checks themselves are 15 minutes old the page
  also says "monitoring delayed" ([status-page-stale](status-page-stale.md)).
- `/admin/system`: every worker pulse stale, the `inbound` lane's due
  jobs and oldest wait growing.

## Check (5 minutes)

1. `curl -s https://<api>/healthz/pipeline | jq` — which check failed:
   `worker` (no process beats) or `inbound` (processes beat but customer
   messages wait: the customer workers are gone or stuck while the batch
   worker runs).
2. Render → `workshop-worker` and `workshop-batch-worker` → Events: a
   failed deploy (build or start command), OOM kills, a crash loop, a
   suspended service (billing)?
3. Logs of a worker: does it start (`Worker lanes started`) and then
   stop? A database error at start (`DATABASE_URL`, roles, migrations not
   applied: `GET /readyz` → `checks.migrations`) keeps every worker down.
4. The database: Render → `workshop-db` → Metrics. A database at its
   connection limit refuses new workers ([database-failover](database-failover.md)).

## Mitigate

- **Crash loop after a deploy:** roll back (Render → the service →
  Rollback to the previous deploy), see [bad-deploy](bad-deploy.md).
- **Hung processes:** Render → `workshop-worker` → Restart. Jobs whose
  lease expired go to the next worker by themselves.
- **OOM:** the job that kills its process twice is set aside
  (`process_died` dead letter) and stops taking workers down; give
  `workshop-batch-worker` more memory if it is a batch job.
- Post a `degraded` (or `outage`) announcement for the chat components on
  `/admin/system` when customers will notice; record the incident with the
  "every business" scope and publish its announcement from the same dialog.

## Fix and recover

- Once a worker beats again, the next look of the watchdog (or the
  workers' own `platform_alerts` job) resolves `worker_down` and sends
  RESOLVED; `/healthz/pipeline` answers 200 when the backlog is drained.
- The waiting customer messages are answered in arrival order; retry the
  dead letters of `process_inbound_message` and `deliver_outbound` that
  ran out of attempts while workers were gone.

## When the watchdog itself is the problem

- `PIPELINE_WATCHDOG_SECONDS=0` switches it off (every API process); the
  Sentry Crons monitor of `platform_alerts` and the uptime monitor on
  `/healthz/pipeline` remain.
- Log lines `The pipeline watchdog skipped a look` mean it could not take
  the alert-state lock in 10 s (another process held it) or reach the
  database; repeated ones point at the database.

## Afterwards

- SEV1 postmortem (`../incident.md`); the minutes without answers count
  against the "answered within 60 s" budget (`../slo.md`).
- Game day: `tests/chaos/test_worker_down_game_day.py` rehearses this page.
