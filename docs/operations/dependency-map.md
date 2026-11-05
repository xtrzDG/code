# Dependency map

What each outside dependency carries, what customers and owners notice
when it fails, what the platform does by itself, and the runbook to open.
Contacts and status pages: `docs/operations/contacts.md`; contracts and exit
plans: `docs/operations/vendor-register.md`. Every runbook named below
exists (`tests/legal/test_operations_documents.py`).

```
 Customers ─┬─ phone ──► carrier forwarding ─► Zadarma / Twilio number ─► ElevenLabs agent ─┐
            ├─ WhatsApp, Instagram, Messenger ─► Meta ───────────────────────────────────────┤
            ├─ Telegram ─► Telegram Bot API ──────────────────────────────────────────────────┤
            └─ website chat, hosted chat, booking links ─────────────────────────────────────┤
                                                                                           ▼
 DNS + TLS (registrar, Render certificates) ─► Render Frankfurt: API ─ workers ─ cabinet ─ Postgres
                                                   │        │
                         OpenAI EU (replies) ◄─────┤        ├─► outbox: Meta, Telegram, Twilio SMS, SMTP e-mail
                  Anthropic (fallback, judge) ◄────┤        ├─► Google Calendar, outbound webhooks
                     Stripe / Flitt (money) ◄──────┤        └─► EU object storage (recordings, backups)
            Sentry, Langfuse, OTLP (insight) ◄─────┘
 Owners ─► cabinet (Render) ─► login codes: SMS (Twilio), e-mail (SMTP), WhatsApp (Meta), Telegram Gateway
```

## When a dependency fails

| Dependency | What breaks | What happens by itself | Severity | Runbook |
| --- | --- | --- | --- | --- |
| Render (region) | everything | providers retry webhooks; jobs wait in the database | SEV1 | [render-outage](runbooks/render-outage.md) |
| Postgres (`workshop-db`) | everything that reads or writes | API answers 502, workers keep polling, webhooks retried | SEV1 | [database-failover](runbooks/database-failover.md) |
| DNS or certificates | every public host, provider webhooks | resolvers' caches hide it for up to a TTL | SEV1 | [dns-outage](runbooks/dns-outage.md) |
| The workers | answers, notifications, reminders | the API's watchdog pages `worker_down` | SEV1 | [worker-down](runbooks/worker-down.md) |
| OpenAI | the assistant's replies | the circuit opens, Anthropic answers; else handoff to staff | SEV1 | [llm-outage](runbooks/llm-outage.md) |
| Anthropic | the fallback model, autotests' judge | none needed while OpenAI answers | SEV3 | [llm-outage](runbooks/llm-outage.md) |
| ElevenLabs | calls | rented numbers put calls through to the staff mobile on duty | SEV2 | [voice-outage](runbooks/voice-outage.md) |
| Zadarma | calls on its numbers | none: calls to its numbers do not reach the agent | SEV2 | [voice-outage](runbooks/voice-outage.md) |
| Twilio | SMS codes, text-backs, the voice fallback | other code channels; the outbox retries | SEV2 | [sms-outage](runbooks/sms-outage.md) |
| SMTP e-mail | e-mail codes, owners' notices, alert e-mails | alerts still reach the Telegram group; the outbox retries | SEV2 | [email-outage](runbooks/email-outage.md) |
| Meta | WhatsApp, Instagram, Messenger; WhatsApp codes | Meta retries webhooks; the outbox retries sends | SEV2 | [meta-outage](runbooks/meta-outage.md) |
| Telegram | Telegram channels; ops alerts in Telegram | alerts still go by e-mail | SEV2 | [telegram-outage](runbooks/telegram-outage.md) |
| Stripe or Flitt | subscriptions, deposits | the PSP's circuit opens; the PSP retries its webhooks; the booking waits for the deposit | SEV2 | [provider-circuits](runbooks/provider-circuits.md); the PSP monitors of [on-call](on-call.md) |
| Google Calendar | calendar sync of connected businesses | the cabinet's calendar stays the source; sync resumes | SEV3 | none needed: wait, the periodic sync catches up |
| EU object storage | recordings, files, backups | recording archive jobs retry; the nightly backup fails and Sentry Crons pages | SEV2 | [backup-restore](backup-restore.md) |
| Sentry, Langfuse, OTLP | insight only | nothing customers notice; Sentry Crons stops paging, the platform alerts do not | SEV3 | none needed: watch `/admin/system` meanwhile |
| GitHub | CI and new releases | production keeps running the last release | SEV3 | none needed: no release until it is back |

The circuit breakers and the per-provider bulkheads that keep one slow
provider from holding up the others are in
[provider-circuits](runbooks/provider-circuits.md); each likely failure has
a scripted game day in `tests/chaos/`.
