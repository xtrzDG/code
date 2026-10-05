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
| [stuck-worker](stuck-worker.md) | `dead_jobs`, `inbound_backlog`, `stale_worker`, Sentry Crons | SEV1-SEV2 |
| [delivery-failures](delivery-failures.md) | `outbound_failures` | SEV2 |
| [assistant-quality](assistant-quality.md) | `handoff_spike`, `tool_errors`, `quality_drop` | SEV2-SEV3 |
| [sms-pumping](sms-pumping.md) | `otp_cap_trips` | SEV2 |
| [spend-spike](spend-spike.md) | provider budget e-mails, margin on Admin → Metrics | SEV2 |
| [bad-deploy](bad-deploy.md) | errors right after a deploy, the smoke test | SEV1-SEV2 |
| [data-breach](data-breach.md) | anyone who suspects one | SEV1, 48 h clock |

Start every incident at `/admin/system`: firing alerts, worker pulses,
queue lanes and dead letters, channels in ERROR, the last backup.
