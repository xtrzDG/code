# Runbooks

One page per failure, each in the same order: how it shows, what to check,
how to stop the harm (mitigate), how to fix it, and what to do afterwards.
Severity, roles and owner communication are in `../incident.md` (the
first-minute decision tree and the hours in `../on-call.md`); the alerts
that link here are in `../slo.md` and `ops/alerts/`; which dependency needs
which runbook is `../dependency-map.md`.

| Runbook | Alerts that link it | Usual severity |
| --- | --- | --- |
| [llm-outage](llm-outage.md) | `llm_errors` | SEV1 |
| [meta-outage](meta-outage.md) | `outbound_failures`, channels in ERROR | SEV2 |
| [telegram-outage](telegram-outage.md) | `outbound_failures` | SEV2 |
| [provider-circuits](provider-circuits.md) | a circuit open on `/admin/system`, `outbound_failures` | SEV2 |
| [voice-outage](voice-outage.md) | `voice_health`, Sentry, owners (calls not answered) | SEV2 |
| [worker-down](worker-down.md) | `worker_down`, `inbound_backlog` (the API's watchdog), `GET /healthz/pipeline` 503 | SEV1 |
| [stuck-worker](stuck-worker.md) | `dead_jobs`, `inbound_backlog`, `stale_worker`, Sentry Crons | SEV1-SEV2 |
| [database-failover](database-failover.md) | `GET /readyz` 503 (uptime monitor), `worker_down` | SEV1 |
| [status-page-stale](status-page-stale.md) | `/status` says "monitoring delayed" | SEV2 |
| [delivery-failures](delivery-failures.md) | `outbound_failures` | SEV2 |
| [assistant-quality](assistant-quality.md) | `handoff_spike`, `tool_errors`, `quality_drop` | SEV2-SEV3 |
| [sms-pumping](sms-pumping.md) | `otp_cap_trips`; "Sign-in codes sprayed" (e-mail and Sentry) | SEV2 |
| [spend-spike](spend-spike.md) | provider budget e-mails, margin on Admin → Metrics | SEV2 |
| [irsf-toll-fraud](irsf-toll-fraud.md) | `spend_spike` with outgoing call legs, the telephony provider's fraud e-mail | SEV2 |
| [stalled-data-task](stalled-data-task.md) | `backfill_stalled`, the data-task card | SEV3 |
| [bad-deploy](bad-deploy.md) | errors right after a deploy, the smoke test | SEV1-SEV2 |
| [data-breach](data-breach.md) | anyone who suspects one | SEV1, 48 h clock |
| [error-budget-burn](error-budget-burn.md) | `answer_budget_fast_burn`, `answer_budget_slow_burn`, `api_budget_fast_burn`, `api_budget_slow_burn` | SEV1-SEV2 |
| [audit-anomaly](audit-anomaly.md) | `bulk_personal_data`, `tenant_hopping`, `failed_sign_in_checks` | SEV2 |
| [audit-chain-broken](audit-chain-broken.md) | `audit_chain_broken`, a broken chain on Admin → Audit | SEV1 |
| [render-outage](render-outage.md) | the uptime monitor's three checks at once, a Render incident | SEV1 |
| [dns-outage](dns-outage.md) | DNS or TLS errors of the uptime monitor, the certificate expiry monitor | SEV1 |
| [sms-outage](sms-outage.md) | `outbound_failures` with Twilio errors, owners without SMS codes | SEV2 |
| [email-outage](email-outage.md) | `outbound_failures` with SMTP errors, owners without e-mail codes | SEV2 |
| [platform-brakes](platform-brakes.md) | `spend_budget_stop`; pausing every assistant (Admin → System) | SEV1 |
| [missed-job-runs](missed-job-runs.md) | `missed_job_runs` (periodic job heartbeats, no Sentry needed) | SEV2 |
| [payment-mismatch](payment-mismatch.md) | `payment_mismatch` (the daily reconciliation with Flitt and Stripe) | SEV2 |
| [webhook-signature-failures](webhook-signature-failures.md) | `webhook_signature_failures` | SEV2 |
| [storage-errors](storage-errors.md) | `storage_errors` (database or object storage) | SEV1 |
| [api-latency](api-latency.md) | `api_latency` | SEV2 |
| [backup-failed](backup-failed.md) | `backup_failed`, the last backup on Admin → System, Sentry Crons | SEV2 |
| [tenant-sms-volume](tenant-sms-volume.md) | `tenant_sms_volume`, `otp_conversion` | SEV2 |
| [tenant-payment-declines](tenant-payment-declines.md) | `tenant_payment_declines` (card testing; new payment pages braked) | SEV2 |
| [booking-abuse](booking-abuse.md) | `booking_spike`, `cancellation_spike` | SEV3 |
| [campaign-opt-outs](campaign-opt-outs.md) | `campaign_opt_outs` (a campaign held over its opt-out rate) | SEV3 |
| [whatsapp-quality](whatsapp-quality.md) | `whatsapp_quality` | SEV2 |
| [privacy-requests](privacy-requests.md) | none: a person asks the platform about their own data (access, copy, correction, erasure) | none; answer within a month |
| [secret-rotation](secret-rotation.md) | none: the yearly rotation, an offboarding or a leak of a webhook secret | none; SEV1 for a leak |

Start every incident at `/admin/system`: firing alerts, worker pulses,
the providers' circuits, queue lanes and dead letters, channels in ERROR, the last backup. Each
likely failure has a scripted game day in `tests/chaos/` (worker killed,
Meta black-holed, model 30 s slow, Postgres restarted) that asserts its
alert, the status level and the recovery; run them before changing a
runbook (`uv run pytest tests/chaos`).

## Game days

The scripted game days run with the backend tests on every pull request,
against a real Postgres and two processes (the API and a worker). The
guards CI cannot replace run on a schedule instead: the restore drill
(`restore-drill.yml`), the latency budgets (`perf.yml`), the nightly
evals (`evals-nightly.yml`), the dynamic scans of the running stack and
of staging (`zap.yml`, `zap-staging.yml`), the nightly dependency audit
(`dependency-audit.yml`), the weekly rescan of the release images
(`image-rescan.yml`), production's hourly synthetic checks
(`synthetics.yml`) and the repository settings check (`repo-settings.yml`).
A silent schedule is a failure too: every
morning `schedule-watch.yml` opens an issue for each of them without a
successful scheduled run in the last 8 days (once per workflow while it is
open; a run by hand or by a pull request does not count). Close the issue
yourself once a scheduled run succeeded again: the watch never closes one.
