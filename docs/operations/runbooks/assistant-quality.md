# Assistant quality: handoff spikes and tool errors

**Alerts:** `handoff_spike` (SEV2): the last hour's handoffs are over 3
times the week before's hourly mean (at least 5); `tool_errors` (SEV3):
over 5 replies in an hour carry a failed tool call.

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
