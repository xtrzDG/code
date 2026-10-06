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

Every SLI is counted in the database (migration 1163,
`docs/operations/observability.md`, "Service level rows"), so every
instance, the error budget card and the alerts read the same figures:

- **Answered in time.** The `record_sli` job (every 5 minutes) judges each
  five-minute slot of customer messages once their 60 s are over: an inbox
  event answered or handed off within 60 s of arriving is good; one answered
  later, never, or failed after its retries is bad. A message refused on its
  first try (the business is not live, the message cannot be read) or
  dropped by an erasure is not counted, like a paused assistant. The slots
  live in `service_level_slots`; every hour is summed into
  `service_level_hours`.
- **Answer latency.** The hour row's p95 of `messages.reply_latency_ms`
  (assistant replies stored in that hour), from the latency buckets the
  reply speed page uses. The budget card counts the hours whose p95 was
  above 15 s. Prometheus has the same in
  `workshop_answer_latency_seconds` per channel, and Sentry's traces of
  `process_inbound_message` show where a slow turn spent its time.
- **API availability.** Each API process counts the requests it answers
  (not the probes `/healthz`, `/readyz` or `/metrics`) and those answered
  with a 5xx per slot, and adds them to the shared slots every 15 s. A
  request that never reached the API (a crash, the edge refusing) is not
  in these counts: the external uptime monitor on `GET /readyz` every
  minute (UptimeRobot or Better Stack, EU probe; set it up at launch,
  `docs/LAUNCH.md` 4.9) and Render's HTTP metrics cover that, and Sentry
  shows the errors behind each 5xx.

`/admin/system` shows, per objective, what is left of the 28-day budget
and how fast the last hour burned it (1x spends the budget exactly in 28
days), and the answer p95 against 15 s
(`GET /v1/admin/system/error-budget`). The Grafana dashboard
(`ops/grafana/`) graphs the same objectives from the Prometheus histograms
between those rows.

## Alerts

The `platform_alerts` periodic job (every five minutes, once per period
across workers) checks the rules of `ops/alerts/*.yaml` on persisted state
and shared counters only, never on one process's memory, so a restart
loses nothing and two workers never both page. Each rule fires when its
figure is above its threshold:

| Alert | Fires when | Severity | Runbook |
| --- | --- | --- | --- |
| `dead_jobs` | any queued job ran out of attempts or took its worker down twice (`process_died`) | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `inbound_backlog` | the oldest due customer message has waited over 120 s | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `outbound_failures` | over 10% of the last hour's settled outbox messages died (at least 20) | SEV2 | [delivery-failures](runbooks/delivery-failures.md) |
| `llm_errors` | over 5% of the last 15-30 minutes' model calls failed (at least 20) | SEV1 | [llm-outage](runbooks/llm-outage.md) |
| `handoff_spike` | the last hour's handoffs are over 3 times the week before's hourly mean (at least 5) | SEV2 | [assistant-quality](runbooks/assistant-quality.md) |
| `tool_errors` | over 5 replies of the last hour carry a failed tool call | SEV3 | [assistant-quality](runbooks/assistant-quality.md) |
| `stale_worker` | a worker of the current release has not beaten for 10 minutes while others run | SEV2 | [stuck-worker](runbooks/stuck-worker.md) |
| `worker_down` | no worker at all wrote its pulse for 5 minutes (raised by the API's pipeline watchdog) | SEV1 | [worker-down](runbooks/worker-down.md) |
| `otp_cap_trips` | a platform cap refused a login code in the last 15-30 minutes | SEV2 | [sms-pumping](runbooks/sms-pumping.md) |
| `quality_drop` | the judge's average score of the last day's sampled real conversations is over 10% below the 7 days before (at least 10 scored in each) | SEV3 | [assistant-quality](runbooks/assistant-quality.md) |
| `answer_budget_fast_burn` | the answer budget burns over 14.4 times the sustainable pace in the last hour and the last 5 minutes (at least 20 messages) | SEV1 | [error-budget-burn](runbooks/error-budget-burn.md) |
| `answer_budget_slow_burn` | the answer budget burns over 6 times the sustainable pace in the last 6 hours and the last 30 minutes (at least 20 messages) | SEV2 | [error-budget-burn](runbooks/error-budget-burn.md) |
| `api_budget_fast_burn` | the API budget burns over 14.4 times the sustainable pace in the last hour and the last 5 minutes (at least 100 requests) | SEV1 | [error-budget-burn](runbooks/error-budget-burn.md) |
| `api_budget_slow_burn` | the API budget burns over 6 times the sustainable pace in the last 6 hours and the last 30 minutes (at least 100 requests) | SEV2 | [error-budget-burn](runbooks/error-budget-burn.md) |

**Burn rates.** The four budget alerts are multi-window burn-rate rules
on the `service_level_slots` rows. A burn rate of 14.4 for an hour spends
2% of the 28-day budget; 6 for six hours spends 5%. Each rule needs its
long window (the size of the problem) and its short window (that it is
still happening) both above the threshold, so it fires within minutes of
a real outage and resolves soon after it ends instead of an hour later.
The customer-message windows end with the newest slot `record_sli` judged
(about two minutes behind), and a rule whose newest slot is older than its
long window stays quiet: a stopped `record_sli` pages through Sentry Crons
and `stale_worker`, not as a burn.

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

**What the job cannot see.** When no worker runs, no check runs. Three
watchers outside the workers cover that:

- **The API's pipeline watchdog.** Every `PIPELINE_WATCHDOG_SECONDS` (60)
  each API process takes a look; the one that holds the watchdog's lease
  (in `platform_monitors`, read and renewed under the same
  `platform-alert-states` advisory lock as the job) reads the freshest
  worker pulse and the oldest due customer message. A pulse older than
  5 minutes (or none) fires `worker_down`; a customer message waiting over
  120 s fires `inbound_backlog`. It steps the same episodes with the same
  cooldown as the job, so whichever looks first tells the team once, and
  it sends straight through the platform bot and SMTP: the job queue
  needs the workers that are gone. Another API process takes the lease
  once the leader stops renewing it (2.5 intervals).
- **The external uptime monitor, two checks.** `GET /readyz` every minute
  (this API instance and the database answer) and `GET /healthz/pipeline`
  every minute (503 while no worker pulsed for 5 minutes or a customer
  message waited over 120 s; the body names which). Both without a token,
  EU probe, alert after two failures. Render routes traffic by `/readyz`
  only: a dead worker must never take the API out of rotation.
- **Sentry Crons** expects a check-in of `platform_alerts` every five
  minutes (with `SENTRY_DSN`; a missed one pages from Sentry).

Configure the monitor's two checks and Sentry Crons at launch.

**Status page freshness.** The job marks every run (`platform_monitors`,
`alert_checks`). `/status` trusts the alert levels only while that mark
is at most 15 minutes old: past that the chat channels (website chat,
Meta, Telegram) count as at least degraded, `GET /v1/platform/status`
says `monitoring_delayed`, and the page shows when the last check ran
([status-page-stale](runbooks/status-page-stale.md)). The hourly history
records those hours the same way.

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
