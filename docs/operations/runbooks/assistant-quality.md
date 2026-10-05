# Assistant quality: handoff spikes, tool errors and quality drops

**Alerts:** `handoff_spike` (SEV2): the last hour's handoffs are over 3
times the week before's hourly mean (at least 5); `tool_errors` (SEV3):
over 5 replies in an hour carry a failed tool call; `quality_drop` (SEV3):
the judge's average score of the real conversations sampled in the last
day is over 10% below the 7 days before (at least 10 scored in each).

## How it shows

- Owners' inboxes fill with "the assistant passed this to you"; staff
  notifications per handoff.
- Tool errors: bookings, prices, availability or the calendar fail inside
  replies; the assistant apologises or hands off.

## Check

1. A deploy in the last hours? Prompt, model or tool changes are the usual
   cause: compare with the deploy time ([bad-deploy](bad-deploy.md)).
2. The model: did `LLM_MODEL_ID` or the provider change? Is the provider
   degraded ([llm-outage](llm-outage.md))?
3. One business or many? Admin → Clients shows each business's health;
   a spike in one business is often its own change (new knowledge, a
   closed calendar, a holiday).
4. Tool errors: the conversation card shows each failed tool call and its
   error. Google Calendar errors (token revoked) show on the business's
   calendar connection; availability errors after an owner edited hours or
   resources.

5. Quality drop: the nightly sample (`sample_conversation_quality`, about
   QUALITY_SAMPLE_PERCENT of the day's conversations, cost-capped by
   QUALITY_SAMPLE_BUDGET_CENTS) scores real conversations on the
   autotests' five criteria. Admin → Clients → a client shows its daily
   trend and its lowest-scored conversations; open the cabinet (with a
   reason) to read one: its card shows the judge's notes. Several
   businesses at once points at a deploy or the model; one business at
   its own changes (a new version, new knowledge). A changed
   `LLM_JUDGE_MODEL_ID` also moves every score: compare with its deploy.

## Mitigate

- Our deploy: roll back ([bad-deploy](bad-deploy.md)).
- One business: tell the owner what fails and how to fix it (reconnect
  Google Calendar, correct hours or resources); autotests (Assistant →
  Tests) show whether the fix holds before it goes live.
- A model degradation: switch provider or model as in
  [llm-outage](llm-outage.md).

## Afterwards

- Add the failing conversation as an evaluation case (`evals/datasets/`)
  so the nightly evaluation catches it next time.
- If the alert paged without a real problem, adjust its threshold in
  `ops/alerts/` with the reason.
