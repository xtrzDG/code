# Voice outage: ElevenLabs or Zadarma

**Signals:** owners report unanswered calls; Sentry errors from the
ElevenLabs client or the voice webhooks; no `process_post_call` jobs;
missed-call text-backs (`send_text_back`) suddenly frequent.

## How it shows

- **ElevenLabs** (the voice agent): calls connect and drop, or the agent
  is silent; its webhooks (`/v1/voice/...`) fail or stop.
- **Zadarma** (the numbers): calls never reach the agent; the PBX webhook
  stops; numbers ring out.

## Check

1. status.elevenlabs.io and Zadarma's notices (my.zadarma.com, support).
2. Sentry: 401 from ElevenLabs means `ELEVENLABS_API_KEY` was revoked;
   region errors mean `ELEVENLABS_API_BASE_URL` points outside the EU
   while `ELEVENLABS_ALLOW_NON_EU_REGION` is false.
3. One business or all: one business's agent disabled or its number's
   forwarding changed by the owner.

## Mitigate

- Tell affected owners (template in `../incident.md`) to forward their
  number to a person for the duration: in Zadarma's cabinet (call
  forwarding) or their phone's own forwarding.
- Missed calls are texted back by WhatsApp or SMS when the business has it
  enabled (Settings → Calls): check those jobs run and are not dead.
- **Key revoked:** new key in ElevenLabs (EU residency workspace), set
  `ELEVENLABS_API_KEY` on `workshop-api` (the worker copies it), redeploy.

## Fix and recover

- Post-call jobs (summaries, recordings) that died: retry them from the
  dead letters once the provider answers; recordings are archived from the
  provider while it keeps them.

## Afterwards

- Postmortem for SEV2: how many calls were missed (Zadarma call log), and
  whether text-back covered them.
