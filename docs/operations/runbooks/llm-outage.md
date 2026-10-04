# Language model outage

**Alert:** `llm_errors` (SEV1): over 5% of the model calls of the last
15-30 minutes failed at the provider, with at least 20 calls.

## How it shows

- Customers get "one moment" replies or none; the inbound lane's oldest
  wait grows on `/admin/system`; dead letters of `process_inbound_message`.
- Sentry: `ExternalServiceError` from the OpenAI or Anthropic client
  (timeouts, 429, 5xx); the log line `Platform alert llm_errors firing`.

## Check (5 minutes)

1. The provider's status page: status.openai.com or status.anthropic.com
   (EU region). An announced incident settles the cause.
2. Sentry, grouped by error: 429 means our rate limit or quota (spend
   limits on the provider's billing page), 401 a revoked key, 5xx and
   timeouts the provider.
3. Did we deploy in the last hour? Then it may be ours: see
   [bad-deploy](bad-deploy.md).

## Mitigate

- **Provider down or rate limited, the other configured:** switch
  `LLM_PROVIDER` (`openai` / `anthropic`) and its model variables in the
  `workshop-backend` env group, then redeploy `workshop-api` and
  `workshop-worker` (Render → Manual deploy → same commit). Both need their
  key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`).
- **Quota or spend limit:** raise it on the provider's billing page; check
  [spend-spike](spend-spike.md) first so the limit is not hiding abuse.
- **Key revoked:** create a new key in the EU project and set it on
  `workshop-api` (the worker copies it); redeploy.
- Lower the load while degraded: `LLM_MAX_CONCURRENCY` (per process) keeps
  calls from piling up on a slow provider.

## Fix and recover

- Messages that failed are retried by the queue with backoff; those that
  ran out of attempts are dead letters. Once calls succeed again, retry
  them on `/admin/system` (Dead letters → Retry): customers get their
  answer late rather than never. Discard only messages older than a day
  (the customer has moved on; the conversation is in the owner's inbox).
- The alert resolves by itself once the error rate drops; the RESOLVED
  message closes the episode.

## Afterwards

- Owners told per `../incident.md` (SEV1: within the hour).
- Postmortem: was the second provider ready? Note the minutes of answers
  lost against the "answered in time" budget.
