# E-mail outage (SMTP provider)

**Alerts:** `outbound_failures` with SMTP errors among the dead letters;
`SMTP_*` errors in the logs; owners report missing login codes by e-mail or
missing notices; the e-mail provider's status page
(`docs/operations/contacts.md`).

The e-mail provider carries login codes by e-mail, the owners' notices
(new bookings, breach notices of DPA 12.1, sub-processor notices) and the
platform alerts to `PLATFORM_ALERT_EMAILS`. The alerts also go to the ops
Telegram group, so the team still hears them.

## Check

1. The provider's status page and dashboard: sending paused, the account
   suspended, a quota reached?
2. The logs' SMTP reply: 535 is a wrong or revoked `SMTP_PASSWORD`; 550 or
   554 with "policy" is a reputation block; timeouts are the provider.
3. Deliverability instead of sending: mail leaves but lands in spam. Check
   SPF, DKIM and DMARC of the sending domain (`SMTP_FROM`) and the
   provider's bounce and complaint rates.

## Mitigate

- Login codes: owners sign in with SMS, WhatsApp or Telegram codes meanwhile;
  say so on the status page.
- A breach notice cannot wait: the 48 hours of DPA 12.1 run regardless.
  Owners who sign in with a phone number get it by SMS anyway
  (`docs/operations/incident.md`); call the others from the support line
  and record each call in the timeline.
- A suspended account or a long outage: switch to the second SMTP provider
  of the vendor register's exit plan (change the `SMTP_*` variables,
  redeploy) and add its SPF and DKIM records first.

## Fix and recover

- Retry the dead letters of `deliver_outbound` once mail flows; discard
  login codes older than 10 minutes.

## Afterwards

- A reputation block: find the cause (a burst of bounces, an import of bad
  addresses) before the next large send; record it in the postmortem.
