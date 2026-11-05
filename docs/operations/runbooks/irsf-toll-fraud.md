# Toll fraud (IRSF) on calls

International revenue share fraud: someone makes the platform pay for
calls to numbers whose operator shares the revenue (premium, satellite,
some small countries), by getting a call transferred or dialled there, or
by abusing a rented number's outgoing leg. One night can cost thousands of
euros.

**Alert:** `spend_spike` (SEV2, `ops/alerts/spend_spike.yaml`): today's
provider spend is more than three times the week's daily mean. Also: the
telephony provider's own fraud or balance e-mail (Twilio, Zadarma), a
business reporting calls it did not make, or `voice_health` with many
short calls.

## How it shows

- Outgoing legs (transfers, fallback dials) to numbers outside the
  business's country, or many to one number, often at night or at a
  weekend.
- A staff number changed shortly before, in a business with a new or
  unverified owner.
- The provider's call log shows long calls to the same foreign prefix.

## Why it is unlikely, and what still allows it

Destinations come only from the business's saved staff numbers, never
from the caller or the model, and must be an ordinary mobile or landline
of the business's country or of an EU member state; premium, shared-cost,
satellite and international special ranges are refused when the number is
saved and again before every dial
(`app/utilities/channels/transfer_destinations.py`). Calls are capped per
business by concurrency and by daily minutes
(`app/use_cases/voice/call_admission.py`). What remains: an attacker who
controls a business's account saves a legitimate-looking EU mobile that
forwards on to a premium number; a compromised provider console or API
key; a provider-side setting that allows outgoing calls from a rented
number.

## Check

1. The provider's console (Twilio: Monitor → Calls, filter outbound;
   Zadarma: call statistics): destinations, durations and cost of the
   last 24 hours. Which business's number or trunk placed them.
2. In `/admin/system` and the business's audit log: who changed the staff
   numbers (Settings → Calls) and when; was it after a new sign-in from a
   new device?
3. Is the destination in the business's own country? Does it answer as
   the business's staff?

## Contain (first 15 minutes)

1. Stop the outgoing legs of the business: Admin → the business → pass
   every customer to the team or pause its assistant
   (`docs/operations/runbooks/platform-brakes.md` for every business at
   once), and remove the staff numbers of its transfers.
2. At the provider: block outbound calls to the abused countries
   (Twilio: Voice → Settings → Geo permissions; Zadarma: the account's
   outgoing call restrictions), lower the account's spending limit, and
   if a key may be leaked rotate it (`docs/operations/runbooks/secret-rotation.md`).
3. If an owner account was taken over: end its sessions, tell the owner
   (`docs/operations/runbooks/data-breach.md` when customers' data was
   reached).

## Afterwards

- Ask the provider for a fraud refund with the call records; most refund
  only when told within days.
- Add the abused prefixes to the refused ranges in
  `app/utilities/channels/transfer_destinations.py` with a test, if the
  numbering plan let them through as ordinary numbers.
- Postmortem when the cost passed a normal day's telephony spend, and
  record the cost in the risk register's row R05
  (`docs/security/risk-register.md`).
