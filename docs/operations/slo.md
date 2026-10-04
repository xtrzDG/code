# Service levels, alerts and the error budget

What the platform promises the businesses it answers for, how each promise
is measured, what pages the team when it is at risk, and what happens when
the budget runs out. `docs/operations/incident.md` covers what to do once
something is wrong; `docs/operations/runbooks/` has one page per failure.

## Objectives

Measured over a rolling 28 days, for all businesses together (sandbox
conversations and autotests excluded).

| SLO | Target | Budget in 28 days | Measured from |
| --- | --- | --- | --- |
| **Answered in time**: a customer message gets the assistant's reply or a handoff to a person within 60 s of arriving | 99.5% of inbound messages | 0.5%: about 1 in 200 messages may be later or go unanswered | the inbound message's `created_at` to the first assistant reply or handoff of that conversation after it |
| **Answer latency**: the time from a customer message to the assistant's reply | p95 under 15 s | the p95 of any rolling day above 15 s spends a day of budget | the same pairs, replies only |
| **API availability**: requests of the cabinet, the widget and the webhooks answered without a server error | 99.9% of requests | 0.1%: about 40 minutes of full outage in 28 days | responses with status 5xx or none (timeouts, connection refused at the edge) over all responses |

Why these numbers: a customer writing to a business expects a human-like
pace. A reply after a minute reads as "nobody is there", which is the
problem the product solves (concept, section 1). The model itself takes
2-10 s; 15 s at p95 leaves room for tools (bookings, the calendar) and a
retry. 99.9% availability matches what one Render region and a managed
Postgres deliver without heroics.

What does not count against the budgets: messages a business sent while
its assistant was paused or off, sandbox and autotest conversations,
requests refused by design (4xx, rate limits), and planned maintenance
announced 24 h before (on the status page once it exists, R13; until then
by e-mail to owners).

## How each SLO is read today

- **Answered in time.** Each inbound job logs its pickup delay
  (`pickup_delay_ms`, `docs/operations/capacity.md`, "Pickup"), and each
  turn its duration in the conversation log. The early signal is the
  `inbound_backlog` alert: a customer message waiting more than 120 s for
  a worker means this SLO is being spent right now. The exact SLI is a
  query over `messages` (first assistant reply or handoff after each
  inbound message); the metrics pipeline of W15 (OpenTelemetry) turns it
  into a dashboard and a burn-rate alert.
- **Answer latency.** The same pairs, replies only. The metrics pipeline
  (W15) reports the p95 per day; until it does, Sentry's traces of
  `process_inbound_message` (sampled at `SENTRY_TRACES_SAMPLE_RATE`) give
  the distribution, and the `llm_errors` alert catches the most common
  cause, a slow or failing provider.
- **API availability.** Render's HTTP metrics per service (5xx rate) and
  an external uptime monitor on `GET /readyz` every minute (UptimeRobot or
  Better Stack, EU probe; set it up at launch, `docs/LAUNCH.md` 4.9).
  Sentry shows the errors behind each 5xx.

## Alerts

The `platform_alerts` periodic job (every five minutes, once per period
across workers) checks the rules of `ops/alerts/*.yaml` on persisted state
and shared counters only, never on one process's memory, so a restart
loses nothing and two workers never both page. Each rule fires when its
figure is above its threshold:

| Alert | Fires when | Severity | Runbook |
| --- | --- | --- | --- |
| `dead_jobs` | any queued job ran out of attempts | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `inbound_backlog` | the oldest due customer message has waited over 120 s | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `outbound_failures` | over 10% of the last hour's settled outbox messages died (at least 20) | SEV2 | [delivery-failures](runbooks/delivery-failures.md) |
| `llm_errors` | over 5% of the last 15-30 minutes' model calls failed (at least 20) | SEV1 | [llm-outage](runbooks/llm-outage.md) |
| `handoff_spike` | the last hour's handoffs are over 3 times the week before's hourly mean (at least 5) | SEV2 | [assistant-quality](runbooks/assistant-quality.md) |
| `tool_errors` | over 5 replies of the last hour carry a failed tool call | SEV3 | [assistant-quality](runbooks/assistant-quality.md) |
| `stale_worker` | a worker of the current release has not beaten for 10 minutes while others run | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `otp_cap_trips` | a platform cap refused a login code in the last 15-30 minutes | SEV2 | [sms-pumping](runbooks/sms-pumping.md) |

**Episodes and cooldown.** An alert that starts firing is sent at once
("FIRING"). While it keeps firing it is sent again only after
`PLATFORM_ALERT_COOLDOWN_MINUTES` (60) since the last message ("STILL
FIRING"), and once when it stops ("RESOLVED"). The episode lives in the
`platform_alert_states` collection, so the cooldown holds across restarts
and workers.

**Where they go.** Every message goes to each chat of
`PLATFORM_ALERT_TELEGRAM_CHAT_IDS` through the platform bot and to each
address of `PLATFORM_ALERT_EMAILS`, as its own `send_platform_alert` job in
the outbound lane: a provider outage delays an alert (the queue retries
with backoff and keeps it as a dead letter) instead of losing it. The
first line names the severity, the state and the alert; the message ends
with the runbook and the link to the system page. Without recipients the
alerts are logged (warning) and shown on the system page.

**The system page.** `/admin/system` (GET `/v1/admin/system`) shows the
firing alerts and those resolved within a day, next to everything an
on-call person needs first: worker pulses, each queue lane's waiting,
scheduled, running and dead jobs with the oldest wait, the dead letters by
job (retry or discard them there), channels in ERROR and Meta tokens that
run out within two weeks (the hourly `check_channel_credentials` job asks
Meta about each token once a day; it needs `META_APP_ID` and
`META_APP_SECRET`), the database size per table, and the last backup and
restore drill. Every figure is an indexed count or the system catalog.

**What the job cannot see.** When no worker runs, no check runs. Two
outside watchers cover that: Sentry Crons expects a check-in of
`platform_alerts` every five minutes (with `SENTRY_DSN`; a missed one
pages from Sentry), and the external uptime monitor on `GET /readyz`
catches the API and the database. Configure both at launch.

**Changing a rule.** Edit its file in `ops/alerts/` and
`app/use_cases/admin/alerts/alert_rules.py` in the same pull request
(`tests/platform_ops/test_alert_rules_as_code.py` keeps them equal) and
say in the description why the threshold moves: after an incident's
postmortem, or because it paged without a real problem twice in a month.

## Error budget policy

The budget is what the SLO allows to fail. It is reviewed every Monday
with the restore drill's result (`docs/operations/backup-restore.md`).

| Budget left (28 days) | What happens |
| --- | --- |
| More than 50% | Normal work. Risky changes (migrations of large tables, provider switches) ship on weekdays before 15:00 Tbilisi time. |
| 50% to 0% | Every deploy names its rollback in the pull request; no Friday deploys; the on-call person reviews the burn each morning. |
| Spent | Feature work stops for the area that spent it: only fixes, tests and reliability work ship until the 28-day window is back above zero. A SEV1 or SEV2 postmortem's action items go first. |
| Spent twice in a quarter | The objective or the architecture is wrong: revisit the target with the founder, or plan the structural fix (more workers, a second model provider, a second region) before new features. |

One incident that spends more than 20% of a budget at once gets a
postmortem whatever its severity (`docs/operations/incident.md`).
Exceptions (a provider's announced outage, a launch week) are decided by
the founder and written into the postmortem, never silently.
