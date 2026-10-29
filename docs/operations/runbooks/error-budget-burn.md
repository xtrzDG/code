# Error budget burn: an SLO is being spent too fast

**Alerts:** `answer_budget_fast_burn` (SEV1) and `answer_budget_slow_burn`
(SEV2) for "answered in time" (99.5% of customer messages answered or
handed off within 60 s); `api_budget_fast_burn` (SEV1) and
`api_budget_slow_burn` (SEV2) for API availability (99.9% of requests
without a server error). The rules are in `ops/alerts/*_budget_*_burn.yaml`
and come through the platform alerts job like every other alert (one
message, then again at most once per cooldown, then RESOLVED).

A burn rate of 100% spends the 28-day budget in exactly 28 days. The fast
rules fire at 1440% (14.4 times: the whole budget in about two days)
measured over the last hour **and** the last 5 minutes; the slow rules at
600% over the last 6 hours **and** the last 30 minutes. The short window
makes an alert stop soon after the cause stops; the long one keeps a
single bad minute from paging. The figure in the message is the long
window's burn rate.

**Where the numbers come from.** The `record_sli` job (every 5 minutes)
judges each five-minute slot of customer messages once the last of them
had its 60 s, and each API process adds its requests and 5xx answers to
the shared slots every 15 s (`service_level_slots`, migration 1163). The
hourly rows (`service_level_hours`) feed the error budget card on
`/admin/system`.

## Check

1. `/admin/system`: the error budget card (budget left per SLO, the last
   hour's burn rate, answer p95) and the other firing alerts. A burn
   alert rarely comes alone: `inbound_backlog`, `llm_errors`,
   `stale_worker`, `dead_jobs` or `outbound_failures` usually name the
   cause.
2. Answer budget: is the inbound lane waiting (`inbound_backlog`, lane
   depth on the page, `workshop_queue_oldest_wait_seconds{lane="inbound"}`
   in Grafana)? Are model calls slow or failing
   (`workshop_llm_call_duration_seconds`, `llm_errors`)? Did a deploy just
   happen ([bad-deploy](bad-deploy.md))?
3. API budget: which route answers 5xx? Grafana's "HTTP" row
   (`workshop_http_request_duration_seconds_count{status_class="5xx"}` by
   route), Sentry's issues of the last hour, Render's service metrics.
   Is the database pool exhausted (`workshop_db_pool_wait_seconds`)?
4. Is it one business? The burn counts every business together; a single
   business's traffic spike or broken channel can still spend it. The
   admin client list and the conversation logs show who.

## Mitigate

- Follow the runbook of the alert that names the cause:
  [stuck-worker](stuck-worker.md), [llm-outage](llm-outage.md),
  [delivery-failures](delivery-failures.md), [bad-deploy](bad-deploy.md).
- More inbound capacity: raise `WORKER_LANE_CONCURRENCY` for the inbound
  lane or add a worker instance (`docs/operations/capacity.md`).
- A bad release: roll back first, investigate after.
- A failing model provider: fail over as [llm-outage](llm-outage.md)
  describes; the circuit breakers' state is on the Grafana "Resilience"
  row (`workshop_circuit_breaker_state`).

## Afterwards

- A SEV1 burn, or any incident that spent more than 20% of a budget,
  gets a postmortem (`docs/operations/incident.md`).
- Apply the error budget policy of `docs/operations/slo.md`: below 50%
  left, deploys name their rollback; spent, feature work stops for the
  area that spent it.
- A burn alert that paged without a real problem twice in a month: move
  its threshold or floor in `ops/alerts/` and `burn_rate_rules.py` in one
  pull request, with the reason.
