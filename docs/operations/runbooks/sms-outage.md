# SMS outage (Twilio)

**Alerts:** `outbound_failures` with Twilio errors among the dead letters;
the Twilio circuit open on `/admin/system`
([provider-circuits](provider-circuits.md)); owners report that login codes
by SMS do not arrive; a Twilio incident on https://status.twilio.com.

Twilio carries login codes by SMS, staff notifications by SMS, the
text-back to callers who could not get through, and the voice fallback of
rented numbers. Abuse (premium destinations, a flood of code requests) is
[sms-pumping](sms-pumping.md) instead.

## What already happens by itself

- Login codes have other channels: e-mail, WhatsApp
  (`WHATSAPP_OTP_*`) and Telegram (`TELEGRAM_GATEWAY_API_TOKEN`) where set;
  an owner who cannot get an SMS code signs in with e-mail.
- The outbox retries every send with backoff and keeps what failed as a
  dead letter; nothing is lost silently.

## Check

1. Twilio's status page, then the console's error log: which error codes?
   20003 is a revoked or wrong `TWILIO_AUTH_TOKEN`
   (`docs/security/secrets-inventory.md`); 21408 is the destination
   country's geo permissions; 21612 a destination the sender cannot
   reach; 30007 is carrier filtering.
2. All destinations or one country? One country: geo permissions or the
   sender (`TWILIO_FROM_NUMBER`, `TWILIO_MESSAGING_SERVICE_SID`) not
   allowed there.
3. Our last deploy changed a `TWILIO_*` variable? [bad-deploy](bad-deploy.md).

## Mitigate

- Tell owners on the status page that SMS codes are delayed and that
  e-mail sign-in works.
- Text-backs: they are a convenience; let them wait in the queue.
- A revoked token: rotate it (secondary auth token, then promote) and
  redeploy.

## Fix and recover

- Retry the dead letters of `deliver_outbound` once Twilio delivers again;
  discard login codes older than their lifetime (`OTP_LIFETIME_SECONDS`,
  10 minutes) and text-backs older than a day (they would only confuse).

## Afterwards

- Postmortem when it lasted over an hour; consider a second SMS provider if
  it happens twice in a quarter.
