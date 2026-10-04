# Platform alert rules

One file per alert of the `platform_alerts` job (every five minutes, once
per period across workers; `app/use_cases/admin/alerts/`). The files are
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
| `unit` | `count`, `seconds`, `percent` or `ratio` |
| `window_minutes` | how far back the check reads |
| `volume_floor` | the fewest events before a rate means anything |
| `source` | the table and index the check reads (indexed counts only) |
| `runbook` | what to do, linked from every message |

How alerts reach people, their cooldown (`PLATFORM_ALERT_COOLDOWN_MINUTES`)
and the episode rules (firing, still firing after the cooldown, resolved
once) are in docs/operations/slo.md, "Alerts".
