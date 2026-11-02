# On call: hours, severity and the owner's monitors

How fast the team answers, how to pick a severity in the first minute, and
the monitors outside the platform that the owner sets up because the
platform cannot watch them itself. The roles, the timeline and the owner
notices of an incident are in `docs/operations/incident.md`; the rota
itself in `docs/operations/go-live.md`, step 9; phone numbers and provider
contacts in `docs/operations/contacts.md`.

## Hours (Europe/Rome)

All times are Italian time (Europe/Rome, CET in winter, CEST in summer),
the time zone of the first market. Restaurants, salons and hotels work
evenings and weekends, so the day of the rota does too.

| Severity | First answer | When |
| --- | --- | --- |
| SEV1 | within 15 minutes | at any hour, every day |
| SEV2 | within 30 minutes | 08:00-23:00 every day, weekends and holidays included; at 08:00 for one raised overnight |
| SEV3 | next working day | Monday to Friday, 09:00-18:00 |

Owners are told in their business's own time zone (the templates of
`docs/operations/incident.md`). Timelines and postmortems use UTC, with
the Rome time next to the first entry.

## Picking a severity

Answer the questions in order; the first "yes" decides. When unsure, take
the higher one: lowering it later costs nothing.

```
1. Could personal data be exposed, lost or changed by someone who
   should not (a leak, a cross-business view, a stolen token)?
      yes -> SEV1, runbooks/data-breach.md (the 48-hour clock starts now)
2. Is money moving wrongly (a double charge, a deposit marked paid
   without a payment, a refund or payout to the wrong place)?
      yes -> SEV1, and pause the payment flow in the PSP's dashboard
3. Do customers of many businesses get no answer (every chat or the
   voice line for everyone): model, worker, database, Render, DNS?
      yes -> SEV1, the runbook of the failing dependency
             (docs/operations/dependency-map.md)
4. Is one channel, one provider or a group of businesses broken, are
   answers slower than the objective (a fast budget burn), or is a
   protection degraded (SMS pumping, a sign-in flood, a failed backup)?
      yes -> SEV2
5. One business, a workaround exists, or only the cabinet looks wrong?
      yes -> SEV3
```

Alerts carry their usual severity (`docs/operations/slo.md`); the questions
above may raise it (a `voice_health` that leaves every business without
calls is SEV1), never lower a breach.

## Escalation

1. The platform alert, Sentry or the uptime monitor pages the primary of
   the rota; without an acknowledgement in 10 minutes, the secondary.
2. SEV1: the primary calls the founder within 15 minutes, whatever the
   hour, and becomes incident lead until handing over.
3. A provider's fault: open a ticket with the provider at once (support
   addresses in `docs/operations/contacts.md`) and note its number in the
   timeline; check its status page every 30 minutes.
4. A breach: the founder decides about the notices to the businesses
   within the 48 hours of DPA 12.1; each business notifies its own
   supervisory authority (the Garante in Italy), and the platform notifies
   the Garante itself for its own data (`docs/operations/contacts.md`).

## The owner's monitors

These watch what lies outside the code. The owner sets each one up at
launch, routes it to the rota, and checks it in the quarterly access
review (`docs/security/access-review.md`).

| Monitor | Where it runs | Fires when | Then |
| --- | --- | --- | --- |
| TLS certificate expiry of every public host (API, cabinet, website chat, status page) | the uptime monitor's certificate check | under 21 days left (Render's managed certificates renew well before that, so this means a renewal failed) | `runbooks/dns-outage.md`, "Certificates" |
| Domain registration | the registrar's auto-renew and expiry e-mails | under 60 days left, or auto-renew off | renew at once; the founder holds the registrar account |
| Stripe | the Stripe dashboard's e-mail alerts: disputes, failed payouts, Radar's elevated fraud rate, a webhook endpoint failing | any | a failing webhook: `runbooks/payment-mismatch.md` (what the lost notifications changed; resend them from the dashboard) and the webhook secret's row of `docs/security/secrets-inventory.md`; fraud: pause deposits for the affected businesses |
| Flitt | the merchant portal's notifications: chargebacks, settlement failures, a callback failing | any | as Stripe |
| Provider budgets | budget and usage e-mails of OpenAI, Anthropic, ElevenLabs, Twilio, Zadarma | the monthly budget's 50%, 80% and 100% | `runbooks/spend-spike.md` |
| Meta app | the developer dashboard's alerts (webhook failures, app review, policy) | any | `runbooks/meta-outage.md` |
| Uptime | `/readyz`, `/healthz/pipeline` and `/status`, every minute from the EU | two failures in a row | `runbooks/render-outage.md`, `runbooks/worker-down.md` |
| Scheduled jobs | Sentry Crons (every periodic job, the backup) | a run missed or failed | `runbooks/missed-job-runs.md` (the platform's own `missed_job_runs` alert sees the same without Sentry), `runbooks/stuck-worker.md`; the backup: `docs/operations/backup-restore.md` |
| Schedules of the repository | `schedule-watch.yml` issues | a guard without a scheduled run in 8 days | the issue names the workflow |

## Handover

Every Monday at 10:00 the outgoing primary hands over in the ops chat: open
alerts and issues, the error budget left (`/admin/system`), provider
tickets still open, and anything planned for the maintenance window
(`docs/operations/maintenance.md`).
