# SMS volume of a business and unused login codes

**Alerts:**

- `tenant_sms_volume` (SEV2): a business sent more than 60 SMS in an hour
  (staff notifications, missed-call text-backs), or its SMS were refused
  at the cap of 200 an hour. The cap is the automatic throttle: an
  account abused for SMS pumping costs at most 200 messages an hour. A
  warning line of the worker names the business.
- `otp_conversion` (SEV2): more than 70 % of the login codes of the last
  hour were never used (at least 20 settled codes). Codes go to numbers
  nobody signs in with: SMS pumping through sign-in. The message names the
  countries with the most unused codes.

## Check

1. Which business? Search the worker logs for "SMS this hour" lines with
   its `business_id`; open the client on Admin → Clients.
2. Who received them? Many different numbers in premium-rate countries
   are pumping; one busy evening of missed calls is real traffic.
3. For `otp_conversion`: Twilio's SMS log by country; the platform caps
   (`otp_cap_trips`, [sms-pumping](sms-pumping.md)).

## Mitigate and fix

- Pumping through a business: pause the client's assistant or disable
  its text-back on Admin → Clients, and contact the owner.
- Pumping through sign-in: lower the per-country cap of login codes
  (`OTP_SENDS_PER_COUNTRY_PER_HOUR`), add the country to
  `OTP_HIGH_RISK_COUNTRIES` or its prefixes to `OTP_DENIED_PHONE_PREFIXES`
  ([sms-pumping](sms-pumping.md)); Twilio's geo permissions block the
  countries the platform does not serve.
- A legitimate busy business: nothing to do below the cap; tell the owner
  when the cap refused SMS.

## Afterwards

The alerts resolve once the windows are quiet. Record the destinations
and the cost in the incident record; report pumping to Twilio.
