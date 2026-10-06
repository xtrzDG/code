# Runbooks

One page per failure, each in the same order: how it shows, what to check,
how to stop the harm (mitigate), how to fix it, and what to do afterwards.
Severity, roles and owner communication are in `../incident.md`; the alerts
that link here are in `../slo.md` and `ops/alerts/`.

| Runbook | Alerts that link it | Usual severity |
| --- | --- | --- |
| [llm-outage](llm-outage.md) | `llm_errors` | SEV1 |
| [meta-outage](meta-outage.md) | `outbound_failures`, channels in ERROR | SEV2 |
| [telegram-outage](telegram-outage.md) | `outbound_failures` | SEV2 |
| [voice-outage](voice-outage.md) | Sentry, owners (calls not answered) | SEV2 |
| [worker-down](worker-down.md) | `worker_down`, `inbound_backlog` (the API's watchdog), `GET /healthz/pipeline` 503 | SEV1 |
| [stuck-worker](stuck-worker.md) | `dead_jobs`, `inbound_backlog`, `stale_worker`, Sentry Crons | SEV1-SEV2 |
| [database-failover](database-failover.md) | `GET /readyz` 503 (uptime monitor), `worker_down` | SEV1 |
| [status-page-stale](status-page-stale.md) | `/status` says "monitoring delayed" | SEV2 |
| [delivery-failures](delivery-failures.md) | `outbound_failures` | SEV2 |
| [assistant-quality](assistant-quality.md) | `handoff_spike`, `tool_errors`, `quality_drop` | SEV2-SEV3 |
| [sms-pumping](sms-pumping.md) | `otp_cap_trips` | SEV2 |
| [spend-spike](spend-spike.md) | provider budget e-mails, margin on Admin → Metrics | SEV2 |
| [stalled-data-task](stalled-data-task.md) | `backfill_stalled`, the data-task card | SEV3 |
| [bad-deploy](bad-deploy.md) | errors right after a deploy, the smoke test | SEV1-SEV2 |
| [data-breach](data-breach.md) | anyone who suspects one | SEV1, 48 h clock |
| [error-budget-burn](error-budget-burn.md) | `answer_budget_fast_burn`, `answer_budget_slow_burn`, `api_budget_fast_burn`, `api_budget_slow_burn` | SEV1-SEV2 |

Start every incident at `/admin/system`: firing alerts, worker pulses,
queue lanes and dead letters, channels in ERROR, the last backup. Each
likely failure has a scripted game day in `tests/chaos/` (worker killed,
Meta black-holed, model 30 s slow, Postgres restarted) that asserts its
alert, the status level and the recovery; run them before changing a
runbook (`uv run pytest tests/chaos`).

## Game days

The scripted game days run with the backend tests on every pull request,
against a real Postgres and two processes (the API and a worker). The
guards CI cannot replace run on a schedule instead: the restore drill
(`restore-drill.yml`), the latency budgets (`perf.yml`) and the nightly
evals (`evals-nightly.yml`). A silent schedule is a failure too: every
morning `schedule-watch.yml` opens an issue for each of them without a
successful run in the last 8 days (once per workflow while it is open).
