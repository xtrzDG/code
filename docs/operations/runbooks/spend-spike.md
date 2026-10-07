# Spend spike: model, SMS and voice costs

**Alerts:** `spend_spike` (SEV2): the providers' spend of the current UTC
day is more than 3 times the daily mean of the 7 days before (from $5 a
day). `spend_budget` (SEV2): it passed 80% of the platform's daily budget
`PLATFORM_DAILY_SPEND_BUDGET_USD` (unset: never fires). Both come through
the platform alerts job (`ops/alerts/spend_spike.yaml`,
`ops/alerts/spend_budget.yaml`) and fire again at most once per cooldown.

**Other signals:** "Spend limit" messages from the spend guard (below):
a business passed its soft or hard daily limit. The providers' budget
e-mails (set them: OpenAI or Anthropic usage limits, Twilio usage
triggers, ElevenLabs quota alerts), the margin on Admin → Metrics
dropping, one business's usage far above its package.

## What already holds the spend

The spend guard checks a business's provider spend of its own day
(recorded costs from `usage_events`; planned unit prices where a cost is
missing) before every model turn and every call:

- **Soft limit** (default 5 times the plan's planned daily provider cost,
  `SPEND_SOFT_LIMIT_MULTIPLE`): the assistant answers on a cheaper model
  (`SPEND_SOFT_LIMIT_MODEL_ID`, else the provider's cheap model). The
  owners and the platform team get one message that day.
- **Hard limit** (default 15 times, `SPEND_HARD_LIMIT_MULTIPLE`): until the
  business's midnight the assistant takes requests only. New messages go to
  the team's inbox as handoffs, and the voice agent declines calls, so
  customers get the missed-call text-back. The owners and the platform team
  get one message, and the business's audit log gets `spend_limit_reached`.
- Calls end after `CALL_MAX_DURATION_SECONDS` (600) or
  `CALL_SILENCE_END_SECONDS` of silence. The voice platform applies both
  the next time an agent is provisioned.
- Owner actions have their own limits: test chat 30 a minute per person,
  menu import 10 an hour, autotests 1 running and 20 a day per business.
  On top of that, every API request counts against the generic limits
  (`API_REQUESTS_PER_USER_PER_MINUTE`, `API_EXPORTS_PER_USER_PER_MINUTE`,
  `API_REQUESTS_PER_IP_PER_MINUTE`); past one the API answers 429.

## Check

1. Admin → Clients, the "Spend today" tile (`GET /v1/admin/spend`): today's
   spend by provider, the week's daily mean, the budget used and the
   clients that passed a limit today.
2. Which provider? Their usage pages by day: OpenAI / Anthropic (tokens
   by model), Twilio (SMS by country), ElevenLabs (minutes).
3. Which business? The tile's list, then Admin → Clients (usage and health
   per business) and Admin → Metrics (margin, cost per business).
4. Model tokens: a loop of tool calls or very long replies shows in the
   conversation cards (tool rounds, tokens per message).
5. SMS: is it pumping? See [sms-pumping](sms-pumping.md).
6. Rows written before migration 1142 count only after
   `workshop backfill-lookup --collection usage_events`
   ([deploys](../deploys.md)). Until then a day that began before the
   deploy may read low.

## Mitigate

- One business: lower its limits with
  `PUT /v1/admin/clients/{business_id}/spend-limits`
  (`{"hard_limit_micro_usd": 0}` stops its model turns and calls at once;
  `null` restores the plan's default). The change is written to the
  client's audit log. Raise them the same way for a business with a real
  rush.
- Every business: lower `SPEND_SOFT_LIMIT_MULTIPLE` and
  `SPEND_HARD_LIMIT_MULTIPLE` in the env group `workshop-backend` and
  redeploy.
- One customer flooding a business: the per-contact limit
  (`CONTACT_MESSAGE_LIMIT_PER_HOUR`) stops replies after 60 an hour;
  lower it platform-wide only for the duration.
- A website copying a business's chat: the owner lists the business's own
  sites (Channels → Website chat → "Websites allowed to show the chat").
  Requests from other sites then get 403.
- Runaway replies: lower `LLM_MAX_OUTPUT_TOKENS` or `LLM_TOOL_ROUND_LIMIT`;
  roll back a deploy that changed prompts or tools
  ([bad-deploy](bad-deploy.md)).
- An abusive business: open its cabinet from Admin → Clients (audited),
  switch its channels off and call the owner; billing settles overage on
  its invoice.
- Hard stop: the provider's own spend limit (set it to about twice a
  normal month).

## Afterwards

- Note the cost in the postmortem; if a limit was missing, add it to
  `docs/LAUNCH.md`.
- Set `PLATFORM_DAILY_SPEND_BUDGET_USD` if it was unset, about 1.5 times a
  normal day.
