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

- `LLM_FALLBACK_MODEL_ID=off` turns the failover off: an open circuit then
  fails the turn, the queue retries it with backoff and finally keeps it
  as a dead letter. Use `off` only when the other provider must not see
  customer messages (a contract, a data-residency promise).
- The fallback is tried only when its provider has its key
  (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`); without it the failover is
  silently absent.

## How it shows

- Logs: `The circuit of <provider>:<model> is open: <fallback> answers
  instead.`; Sentry: `ExternalServiceError` from the OpenAI or Anthropic
  client (timeouts, 429, 5xx).
- Grafana "Resilience" row and `/metrics`: `workshop_circuit_breaker_state`
  per circuit (0 closed, 1 half-open, 2 open), per process.
- Customers get "one moment" replies after `CHAT_TURN_DEADLINE_SECONDS`
  (20 s) while a turn waits; the inbound lane's oldest wait grows on
  `/admin/system` only when the fallback fails too.

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
- Messages that failed are retried by the queue with backoff; those that
  ran out of attempts are dead letters. Once calls succeed again, retry
  them on `/admin/system` (Dead letters → Retry): customers get their
  answer late rather than never. Discard only messages older than a day
  (the customer has moved on; the conversation is in the owner's inbox).
- The alert resolves by itself once the error rate drops; the RESOLVED
  message closes the episode. If you switched `LLM_PROVIDER` by hand,
  switch back in daylight once the provider is stable for an hour.

## Afterwards

- Owners told per `../incident.md` (SEV1: within the hour).
- Postmortem: did the failover carry the load (minutes with both circuits
  open)? Note the minutes of answers lost against the "answered in time"
  budget. Game day: `tests/chaos/test_llm_latency_game_day.py`.
