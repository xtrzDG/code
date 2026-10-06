# Stuck worker, backlog and dead jobs

**Alerts:** `inbound_backlog` (a customer message has waited over 120 s
for a worker), `dead_jobs` (jobs ran out of attempts or took their worker
down twice), `stale_worker` (a
worker stopped beating while others run), and Sentry Crons when
`platform_alerts` itself stops checking in (no worker runs at all).

## How it shows

`/admin/system`:

- **Workers**: each process's last pulse; "stale" after 5 minutes. A
  worker whose periodic jobs failed lists them.
- **Queue lanes**: per lane the jobs waiting (due), scheduled (retries,
  later work), running and dead, and the oldest wait. A growing `inbound`
  wait with few running jobs: workers are missing or stuck. Many running
  and a growing wait: the workers are saturated.
- **Dead letters** by job name, with why each died ("Every attempt
  failed", "Took its worker down twice" for `process_died`, "No
  handler"), Retry and Discard.

Two worker services (`../capacity.md`, "Worker roles"):
`workshop-worker` (two instances, lanes `inbound` and `outbound`:
customer replies, sends, reminders) and `workshop-batch-worker` (lanes
`default` and `autotests`: exports, imports, reports, autotests, nightly
jobs). A stuck `inbound` lane is the first; a stuck `default` lane the
second.

## Check

1. Render → `workshop-worker` or `workshop-batch-worker` → Events and
   Logs: crashing (OOM, exit codes), restarting, or deploying? A deploy
   replaces workers: old pulses go stale and are ignored, and running
   jobs are handed back to the queue.
2. Logs: `Picked up job ... after it was due` shows `pickup_delay_ms`
   (`../capacity.md`, "Pickup"); `Job <name> failed:` lines show why jobs
   die.
3. The database: `GET /readyz` on the API; Render → `workshop-db` →
   Metrics (connections, CPU). A worker blocked on the pool or on locks
   looks like a stuck worker.
4. Dead letters: one job name, one cause (the error column). A poison job
   (it fails every time on the same data) is not fixed by retrying.
5. `process_died` dead letters: an attempt of that job ended with its
   worker process twice in a row (killed for memory, crashed). Find the
   job id in the logs: `Picked up job` lines carry `lost_leases`, and the
   job's earlier `Job <name> ... in <n> ms; RSS ...` lines
   `rss_before_mb` / `rss_after_mb` (how much memory it took); Render's
   Events show the OOM kills.

## Mitigate

- **Workers gone or hung:** Render → `workshop-worker` → Restart. Jobs
  whose lease expired are released to the next worker automatically.
- **Saturated:** add worker instances (Render → Scaling) or raise the
  inbound lane's concurrency (`WORKER_LANE_CONCURRENCY`, mind
  `DB_POOL_SIZE` and the model provider's limits; `../capacity.md`).
- **A provider behind the failures:** follow its runbook
  ([llm-outage](llm-outage.md), [meta-outage](meta-outage.md),
  [telegram-outage](telegram-outage.md)); retrying before it recovers only
  produces more dead letters.
- **A poison job:** discard it on the system page (audited), open an issue
  with the job id and error; never retry it in a loop. A `process_died`
  job is already out of the queue (it will not take a third worker
  down); retry it only once the cause is fixed or the batch worker has
  the memory for it (Render → `workshop-batch-worker` → plan).

## Fix and recover

- Retry dead letters once the cause is fixed: customer replies first
  (`process_inbound_message`, `deliver_outbound`), then the rest. Discard
  customer messages older than a day instead (the owner's inbox has them).
- `stale_worker` resolves when a worker replaces the silent one or its
  pulse is purged after a day (a deliberate scale-down leaves a stale
  pulse for that day: note it in the ops chat).

## Afterwards

- SEV1 when customers of many businesses waited over the 60 s objective
  for more than a few minutes; postmortem with the budget spent
  (`../slo.md`).
