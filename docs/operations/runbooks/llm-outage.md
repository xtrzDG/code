# Language model outage

**Alert:** `llm_errors` (SEV1): over 5% of the model calls of the last
15-30 minutes failed at the provider, with at least 20 calls.

## What already happens by itself

Every provider and model has a circuit breaker in each process
(`CircuitBreakerFacilitator`): **5 failures within 60 s open it**; while
it is open nobody waits on that model, and **after 30 s one trial call**
decides (success closes it, failure opens it again). The routing adapter
(`RoutingLlmAdapter`) then reruns the request on
**`LLM_FALLBACK_MODEL_ID`**, the other provider's model (by default
`claude-sonnet-5-5` when `LLM_PROVIDER=openai`, `gpt-5-mini` when it is
`anthropic`), with the same transcript in the provider-neutral form. So
with both keys set a one-provider outage costs customers a few slower
answers, not lost ones.

- `LLM_FALLBACK_MODEL_ID=off` turns the failover off, and with it the
  short cut: with nothing to fail over to, every call still waits up to
  `LLM_CALL_TIMEOUT_SECONDS` (25 s, retried once) before it fails. Use
  `off` only when the other provider must not see customer messages (a
  contract, a data-residency promise).
- Without the fallback's key (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`)
  every fallback call fails at once (`Anthropic is not configured: set
  ANTHROPIC_API_KEY.`); the fallback's circuit opens, and once the
  primary's opens too, turns fail at once (`... and its fallback ... are
  both unavailable`).
- A turn whose model calls fail is not lost: the customer gets the
  handoff notice in their language ("your question went to a colleague",
  with the opening hours when closed), the conversation waits in the
  owner's inbox and staff are notified. Expect `handoff_spike` to fire
  with `llm_errors`.

## How it shows

- Logs: `The circuit of <provider>:<model> is open: <fallback> answers
  instead.`; Sentry: `ExternalServiceError` from the OpenAI or Anthropic
  client (timeouts, 429, 5xx).
- Grafana "Resilience" row and `/metrics`: `workshop_circuit_breaker_state`
  per circuit (0 closed, 1 half-open, 2 open), per process.
- Customers get "one moment" replies after `CHAT_TURN_DEADLINE_SECONDS`
  (20 s) while a turn waits, then the handoff notice when it fails;
  `handoff_spike` fires next to `llm_errors`; /status shows the chat
  channels degraded (from 50% failed calls: outage).

## Check (5 minutes)

1. Which circuits are open: `workshop_circuit_breaker_state` (or the log
   line above). Only the primary open and the fallback closed: customers
   are being answered by the fallback; you have time.
2. The provider's status page: status.openai.com or status.anthropic.com
   (EU region). An announced incident settles the cause.
3. Sentry, grouped by error: 429 means our rate limit or quota (spend
   limits on the provider's billing page), 401 a revoked key, 5xx and
   timeouts the provider.
4. Did we deploy in the last hour? Then it may be ours: see
   [bad-deploy](bad-deploy.md).

## Mitigate

- **The fallback answers (primary open, fallback closed):** no action on
  the providers; post a `degraded` announcement for the chat components
  if answers are slower than usual, and watch the fallback's quota.
- **Both circuits open, or the fallback is off or has no key:** this is
  when switching by hand is still needed. Set `LLM_PROVIDER` (and its
  model variables) to the provider that works in the `workshop-backend`
  env group and redeploy `workshop-api` and `workshop-worker` (Render →
  Manual deploy → same commit). A provider that is up but rate limited
  recovers faster with a lower `LLM_MAX_CONCURRENCY` (per process).
- **Quota or spend limit:** raise it on the provider's billing page; check
  [spend-spike](spend-spike.md) first so the limit is not hiding abuse.
- **Key revoked:** create a new key in the EU project and set it on
  `workshop-api` (the worker copies it); redeploy.

## Fix and recover

- Circuits close by themselves after a successful trial call: no restart
  is needed when the provider recovers.
- Turns that failed were handed off: the conversations wait in the
  owners' inboxes ("needs a person"). Nothing is replayed by itself; a
  job that died for another reason (a crash mid-turn) is a dead letter on
  `/admin/system` (Dead letters → Retry) and answers late rather than
  never. Discard only messages older than a day (the customer has moved
  on; the conversation is in the owner's inbox).
- The alert resolves by itself once the error rate drops; the RESOLVED
  message closes the episode. If you switched `LLM_PROVIDER` by hand,
  switch back in daylight once the provider is stable for an hour.

## Afterwards

- Owners told per `../incident.md` (SEV1: within the hour).
- Postmortem: did the failover carry the load (minutes with both circuits
  open)? Note the minutes of answers lost against the "answered in time"
  budget.
- Game day: `tests/chaos/test_llm_latency_game_day.py` (a 30-second
  provider with `LLM_CALL_TIMEOUT_SECONDS=2` and the failover off: every
  visitor gets the handoff notice, `llm_errors` fires at the next
  five-minute check, /status shows the chat channels down; a fast
  provider answers the next visitor, the circuit closes and the alert
  resolves).
