# Status page monitoring delayed

**Shows:** `/status` says "Monitoring delayed — last check N min ago"
(«последняя проверка N мин назад»), and website chat, WhatsApp/Instagram/
Messenger and Telegram are at least *degraded*.

The status levels come from the platform alerts, which the workers'
`platform_alerts` job checks every five minutes. Each run leaves a mark
(`platform_monitors`, `alert_checks`). When the newest mark is older than
**15 minutes**, nothing vouches for "all systems working" any more, so
`GET /v1/platform/status` reports `monitoring_delayed: true`, the age of
the last check in `checked_at`, and the chat components degraded. The
page never claims health it cannot see.

## Check

1. Is any worker running? `GET /healthz/pipeline` and `/admin/system` →
   Workers. No pulses: follow [worker-down](worker-down.md).
2. Workers run but the job does not: the job runs on the batch worker
   (`workshop-batch-worker`, lane `default`). Its logs: `Job
   platform_alerts failed:` lines say why; Sentry Crons shows missed
   check-ins of `platform_alerts`.
3. The job fails at the lock: `The platform-alert-states lock stayed busy`
   means another process held the alert states longer than 10 s; look
   for a stuck API watchdog look (`The pipeline watchdog skipped a look`).

## Mitigate

- Restart `workshop-batch-worker` (Render → Restart) when it is hung; the
  periodic job runs again in the next five-minute period.
- If the job is broken by a deploy, roll back ([bad-deploy](bad-deploy.md)).
- While it is down, post an announcement on `/admin/system` if customers
  are affected; the banner and `/status` show it regardless of the alerts.

## Recover

- The first successful run writes a fresh mark: the delay note disappears
  and the components return to the levels the alerts give, within a
  minute of the page's next refresh.
- The 90-day history records the delayed hours as degraded only when the
  `record_platform_status` job ran meanwhile; when it could not run either,
  the day shows as having no data, never as healthy.
