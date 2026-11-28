# SMS outage (Twilio)

**Alerts:** `outbound_failures` with Twilio errors among the dead letters;
the Twilio circuit open on `/admin/system`
([provider-circuits](provider-circuits.md)); owners report that login codes
by SMS do not arrive; a Twilio incident on https://status.twilio.com.

Twilio carries login codes by SMS, staff notifications by SMS, the
text-back to callers who could not get through, and the voice fallback of
rented numbers. SMS goes out only while the Twilio account has a sender
(`TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`): without one there
is no SMS to lose (the start-up log says "SMS is off", the cabinet tells
owners why), and calls that do not reach a person are
[voice-outage](voice-outage.md). Abuse (premium destinations, a flood of
code requests) is [sms-pumping](sms-pumping.md) instead.

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
   reach; 30007 is carrier filtering. 30034 is a text to a US number from
   a sender without an approved A2P 10DLC campaign, 30035 from a number
   whose registration is still being configured, 30032 from an unverified
   toll-free number: Twilio accepted these texts, billed them and blocked
   them afterwards. The platform reads no delivery reports yet (no
   StatusCallback), so it counted them as sent: they show only in
   Twilio's error log, never among the dead letters, and a login code
   blocked this way never fell back to WhatsApp.
2. All destinations or one country? One country: geo permissions or the
   sender (`TWILIO_FROM_NUMBER`, `TWILIO_MESSAGING_SERVICE_SID`) not
   allowed there; the US with 30034, 30035 or 30032: the sender is not
   registered.
3. Our last deploy changed a `TWILIO_*` variable? [bad-deploy](bad-deploy.md).

## Mitigate

- Tell owners on the status page that SMS codes are delayed and that
  e-mail sign-in works.
- Text-backs: they are a convenience; let them wait in the queue.
- A revoked token: rotate it (secondary auth token, then promote) and
  redeploy, then re-import the rented numbers in ElevenLabs
  ([secret-rotation](secret-rotation.md)).
- A sender that is not registered for US numbers (30034, 30035, 30032):
  empty `TWILIO_FROM_NUMBER` and `TWILIO_MESSAGING_SERVICE_SID` and
  redeploy. SMS is then off: login codes go by the other channels where
  set (WhatsApp, Telegram, e-mail), and the cabinet shows owners why on
  their SMS contacts and in Settings → Calls. Set the sender again only
  once its registration is approved and the platform reads Twilio's
  delivery reports (`docs/operations/go-live.md`, the table of wave 21's
  variables).

## Fix and recover

- Retry the dead letters of `deliver_outbound` once Twilio delivers again;
  discard login codes older than their lifetime (`OTP_LIFETIME_SECONDS`,
  10 minutes) and text-backs older than a day (they would only confuse).

## Afterwards

- Postmortem when it lasted over an hour; consider a second SMS provider if
  it happens twice in a quarter.
