# SMS pumping and login floods

**Alert:** `otp_cap_trips` (SEV2): a platform-wide cap refused a login code
in the last 15-30 minutes. The platform admins also get one e-mail per cap
an hour (`PLATFORM_ADMIN_EMAILS`) and Sentry an event.

## How it shows

- Login codes to many new numbers of one country or prefix, from few
  addresses; Twilio's spend rises.
- Real owners may be refused a code while a cap is full.

## Check

1. Which cap (the alert and the e-mail name it): per country
   (`OTP_SENDS_PER_COUNTRY_PER_HOUR`), new destinations
   (`OTP_SENDS_PER_HOUR`) or verified users
   (`OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR`).
2. Twilio console → Monitor → Messaging logs: destinations, countries,
   cost of the last hour. Pumping looks like many premium or unusual
   prefixes in one country.
3. Logs and Sentry: the cap alert's warning names the cap, its hourly
   limit and the country; the API's access log shows whether the requests
   come from one network or many.

## Mitigate

- Turn on the bot check if it is off: `TURNSTILE_SITE_KEY` and
  `TURNSTILE_SECRET_KEY` (risky requests must pass it).
- Add the abused country to `OTP_HIGH_RISK_COUNTRIES` (bot check always)
  or its prefixes to `OTP_DENIED_PHONE_PREFIXES` (never sent).
- Twilio → Messaging → Geo permissions: switch off countries the platform
  does not serve.
- Lower the country cap for the duration; real owners can still sign in by
  e-mail or Telegram.

## Afterwards

- Check Twilio's invoice for the period and ask Twilio support about
  fraudulent traffic refunds.
- Postmortem if the spend exceeded a day's normal SMS cost.
