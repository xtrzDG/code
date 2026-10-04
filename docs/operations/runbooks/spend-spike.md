# Spend spike: model, SMS and voice costs

**Signals:** the providers' budget e-mails (set them: OpenAI or Anthropic
usage limits, Twilio usage triggers, ElevenLabs quota alerts), the margin
on Admin → Metrics dropping, one business's usage far above its package.

## Check

1. Which provider? Their usage pages by day: OpenAI / Anthropic (tokens
   by model), Twilio (SMS by country), ElevenLabs (minutes).
2. Which business? Admin → Clients (usage and health per business) and
   Admin → Metrics (margin, cost per business). The daily package check
   (`check_package_usage`) tells owners when they pass their package.
3. Model tokens: a loop of tool calls or very long replies shows in the
   conversation cards (tool rounds, tokens per message).
4. SMS: is it pumping? See [sms-pumping](sms-pumping.md).

## Mitigate

- One customer flooding a business: the per-contact limit
  (`CONTACT_MESSAGE_LIMIT_PER_HOUR`) stops replies after 60 an hour;
  lower it platform-wide only for the duration.
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
