# Platform alert rules

One file per alert of the `platform_alerts` job (every five minutes, once
per period across workers; `app/use_cases/admin/alerts/`). Two of them
(`worker_down`, `inbound_backlog`) are also watched from outside the
workers by the API's pipeline watchdog (every `PIPELINE_WATCHDOG_SECONDS`,
one API process at a time), which shares their episodes and cooldown and
sends straight through the platform bot and SMTP; `GET /healthz/pipeline`
is the external monitor's view of the same two conditions. The files are
the reviewed source of the thresholds: the code's copy
(`app/use_cases/admin/alerts/alert_rules.py`) must match them, and
`tests/platform_ops/test_alert_rules_as_code.py` fails when one changes
without the other. Change a threshold here and in the code in one pull
request, with the reason in the description.

| Field | Meaning |
| --- | --- |
| `code` | the alert's code (`PlatformAlertCode`), also its key on the system page |
| `severity` | `sev1`..`sev3` (docs/operations/incident.md) |
| `summary` | what the rule watches, the second line of every message |
| `measure` | the figure the check computes |
| `threshold` | the alert fires when the figure is **above** it (0: any at all) |
| `unit` | `count`, `seconds`, `percent` or `ratio` (a burn rate is in percent of the sustainable pace) |
| `window_minutes` | how far back the check reads |
| `short_window_minutes` | burn-rate rules only: the second, shorter window that must burn too |
| `volume_floor` | the fewest events before a rate means anything |
| `source` | the table and index the check reads (indexed counts only) |
| `runbook` | what to do, linked from every message |

How alerts reach people, their cooldown (`PLATFORM_ALERT_COOLDOWN_MINUTES`)
and the episode rules (firing, still firing after the cooldown, resolved
once) are in docs/operations/slo.md, "Alerts".
